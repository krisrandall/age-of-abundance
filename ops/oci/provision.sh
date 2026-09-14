#!/usr/bin/env bash
# provision.sh — the podcast server on Oracle Cloud, from the laptop, idempotently.
#
# Needs: the OCI CLI (`uv tool install oci-cli`) and Kris's API key in .secrets/oci/config
# (see ops/SETUP.md). Everything it makes is named/tagged so a rerun finds it instead of
# making a second one. Prints the reserved IP at the end and writes ops/server.env.
#
#   ops/oci/provision.sh            create what is missing
#   ops/oci/provision.sh --status   just show what exists
#
# Reverse: ops/oci/RUNBOOK.md ("Tearing it all down").
set -euo pipefail
REPO=$(cd "$(dirname "$0")/../.." && pwd)
export OCI_CLI_CONFIG_FILE="$REPO/.secrets/oci/config"
export OCI_CLI_SUPPRESS_FILE_PERMISSIONS_WARNING=True
OCI=${OCI:-$(command -v oci || echo "$HOME/.local/bin/oci")}
NAME=podcast-server
TAGS='{"project":"age-of-abundance"}'
SHAPE=${SHAPE:-VM.Standard.E2.1.Micro}
KEY="$REPO/.secrets/podcast_server_key"
ALERT_EMAIL=${ALERT_EMAIL:-kris.randall@gmail.com}

[ -f "$OCI_CLI_CONFIG_FILE" ] || { echo "no $OCI_CLI_CONFIG_FILE — see ops/SETUP.md"; exit 1; }
TENANCY=$(sed -n 's/^tenancy *= *//p' "$OCI_CLI_CONFIG_FILE" | head -1)
COMPARTMENT=${OCI_COMPARTMENT:-$TENANCY}     # the root compartment unless told otherwise
oci() { "$OCI" --config-file "$OCI_CLI_CONFIG_FILE" "$@"; }
q() { oci "$@" --raw-output 2>/dev/null || true; }   # quiet query helper
say() { echo "[provision] $*"; }

# ---- what exists
VCN=$(q network vcn list -c "$COMPARTMENT" --display-name podcast-vcn --lifecycle-state AVAILABLE --query 'data[0].id')
INSTANCE=$(q compute instance list -c "$COMPARTMENT" --display-name "$NAME" --lifecycle-state RUNNING --query 'data[0].id')
[ -n "$INSTANCE" ] || INSTANCE=$(q compute instance list -c "$COMPARTMENT" --display-name "$NAME" --lifecycle-state STOPPED --query 'data[0].id')
PUBIP_ID=$(q network public-ip list -c "$COMPARTMENT" --scope REGION --lifetime RESERVED --query "data[?\"display-name\"=='podcast-ip'] | [0].id")
PUBIP=$(q network public-ip list -c "$COMPARTMENT" --scope REGION --lifetime RESERVED --query "data[?\"display-name\"=='podcast-ip'] | [0].\"ip-address\"")
if [ "${1:-}" = "--status" ]; then
  say "vcn=${VCN:-none} instance=${INSTANCE:-none} reserved-ip=${PUBIP:-none}"
  [ -n "$INSTANCE" ] && oci compute instance get --instance-id "$INSTANCE" --query 'data.{name:"display-name",state:"lifecycle-state",shape:shape,ad:"availability-domain"}' --output table
  exit 0
fi

# ---- network: one VCN, an internet gateway, a default route, 22/80/443 in, one regional subnet
if [ -z "$VCN" ]; then
  say "creating VCN podcast-vcn"
  VCN=$(oci network vcn create -c "$COMPARTMENT" --display-name podcast-vcn --cidr-blocks '["10.0.0.0/16"]' --dns-label podcast --freeform-tags "$TAGS" --wait-for-state AVAILABLE --query data.id --raw-output)
fi
IGW=$(q network internet-gateway list -c "$COMPARTMENT" --vcn-id "$VCN" --query 'data[0].id')
if [ -z "$IGW" ]; then
  say "creating internet gateway"
  IGW=$(oci network internet-gateway create -c "$COMPARTMENT" --vcn-id "$VCN" --is-enabled true --display-name podcast-igw --freeform-tags "$TAGS" --wait-for-state AVAILABLE --query data.id --raw-output)
fi
RT=$(oci network vcn get --vcn-id "$VCN" --query 'data."default-route-table-id"' --raw-output)
if ! oci network route-table get --rt-id "$RT" --query 'data."route-rules"[].destination' --raw-output | grep -q '0.0.0.0/0'; then
  say "adding the default route to the internet"
  oci network route-table update --rt-id "$RT" --force --route-rules "[{\"destination\":\"0.0.0.0/0\",\"destinationType\":\"CIDR_BLOCK\",\"networkEntityId\":\"$IGW\"}]" >/dev/null
fi
SL=$(oci network vcn get --vcn-id "$VCN" --query 'data."default-security-list-id"' --raw-output)
if ! oci network security-list get --security-list-id "$SL" --query 'data."ingress-security-rules"[]."tcp-options".."destination-port-range".min' --raw-output 2>/dev/null | grep -qx 443; then
  say "opening 22, 80 and 443 in the security list"
  oci network security-list update --security-list-id "$SL" --force --ingress-security-rules '[
    {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":22,"max":22}}},
    {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
    {"protocol":"6","source":"0.0.0.0/0","isStateless":false,"tcpOptions":{"destinationPortRange":{"min":443,"max":443}}},
    {"protocol":"1","source":"0.0.0.0/0","isStateless":false,"icmpOptions":{"type":3,"code":4}}
  ]' >/dev/null
fi
SUBNET=$(q network subnet list -c "$COMPARTMENT" --vcn-id "$VCN" --display-name podcast-public --lifecycle-state AVAILABLE --query 'data[0].id')
if [ -z "$SUBNET" ]; then
  say "creating the public subnet"
  SUBNET=$(oci network subnet create -c "$COMPARTMENT" --vcn-id "$VCN" --cidr-block 10.0.0.0/24 --display-name podcast-public --dns-label pub --route-table-id "$RT" --security-list-ids "[\"$SL\"]" --freeform-tags "$TAGS" --wait-for-state AVAILABLE --query data.id --raw-output)
fi

# ---- the reserved public IP: DNS points here, so a rebuilt instance keeps its address
if [ -z "$PUBIP_ID" ]; then
  say "reserving a public IP"
  PUBIP_ID=$(oci network public-ip create -c "$COMPARTMENT" --lifetime RESERVED --display-name podcast-ip --freeform-tags "$TAGS" --wait-for-state AVAILABLE --query data.id --raw-output)
  PUBIP=$(oci network public-ip get --public-ip-id "$PUBIP_ID" --query 'data."ip-address"' --raw-output)
fi

# ---- the ssh key for the instance
if [ ! -f "$KEY" ]; then
  say "generating $KEY"
  ssh-keygen -t ed25519 -N "" -C "podcast-server" -f "$KEY" >/dev/null
fi

# ---- the instance
if [ -z "$INSTANCE" ]; then
  IMAGE=$(oci compute image list -c "$COMPARTMENT" --operating-system "Canonical Ubuntu" --operating-system-version "24.04 Minimal" --shape "$SHAPE" --sort-by TIMECREATED --sort-order DESC --query 'data[0].id' --raw-output)
  [ -n "$IMAGE" ] && [ "$IMAGE" != "null" ] || { say "no Ubuntu 24.04 Minimal image for $SHAPE in this region"; exit 1; }
  USERDATA=$(mktemp)
  python3 - "$REPO/ops/oci/cloud-init.yaml" "$REPO/ops/Caddyfile" > "$USERDATA" <<'PY'
import sys
tpl, caddy = open(sys.argv[1]).read(), open(sys.argv[2]).read()
print(tpl.replace("#CADDYFILE#", "\n".join("      " + l for l in caddy.splitlines())), end="")
PY
  SHAPE_CFG=()
  case "$SHAPE" in *Flex) SHAPE_CFG=(--shape-config '{"ocpus":1,"memoryInGBs":6}');; esac
  # E2.1.Micro lives in only one availability domain; try each until one takes it
  for AD in $(oci iam availability-domain list -c "$COMPARTMENT" --query 'data[].name' --raw-output | tr -d '[]",' ); do
    say "launching $NAME ($SHAPE) in $AD"
    if INSTANCE=$(oci compute instance launch -c "$COMPARTMENT" --availability-domain "$AD" --shape "$SHAPE" "${SHAPE_CFG[@]}" \
        --display-name "$NAME" --image-id "$IMAGE" --subnet-id "$SUBNET" --assign-public-ip false \
        --ssh-authorized-keys-file "$KEY.pub" --user-data-file "$USERDATA" --boot-volume-size-in-gbs 50 \
        --freeform-tags "$TAGS" --wait-for-state RUNNING --query data.id --raw-output 2>/tmp/provision-launch.err); then
      break
    fi
    grep -qiE "capacity|InternalError" /tmp/provision-launch.err && { say "no capacity in $AD: $(head -c 200 /tmp/provision-launch.err)"; INSTANCE=""; continue; }
    cat /tmp/provision-launch.err; exit 1
  done
  rm -f "$USERDATA"
  [ -n "$INSTANCE" ] || { say "could not launch in any availability domain (try again later, or SHAPE=VM.Standard.A1.Flex)"; exit 1; }
fi

# ---- attach the reserved IP to the instance's primary VNIC
VNIC=$(oci compute instance list-vnics --instance-id "$INSTANCE" --query 'data[0].id' --raw-output)
PRIV=$(oci network private-ip list --vnic-id "$VNIC" --query 'data[0].id' --raw-output)
ASSIGNED=$(oci network public-ip get --public-ip-id "$PUBIP_ID" --query 'data."private-ip-id"' --raw-output)
if [ "$ASSIGNED" != "$PRIV" ]; then
  say "attaching $PUBIP to the instance"
  oci network public-ip update --public-ip-id "$PUBIP_ID" --private-ip-id "$PRIV" >/dev/null
fi

# ---- a budget so a charge above the free limits is heard about first
if [ -z "$(q budgets budget list -c "$TENANCY" --query "data[?\"display-name\"=='podcast-budget'] | [0].id")" ]; then
  say "creating a AU\$1/month budget with an alert to $ALERT_EMAIL"
  BUDGET=$(oci budgets budget create -c "$TENANCY" --amount 1 --reset-period MONTHLY --display-name podcast-budget --target-type COMPARTMENT --targets "[\"$TENANCY\"]" --query data.id --raw-output) \
    && oci budgets alert-rule create --budget-id "$BUDGET" --type FORECAST --threshold 100 --threshold-type PERCENTAGE --recipients "$ALERT_EMAIL" --display-name podcast-forecast >/dev/null \
    || say "budget could not be created (do it in the console: Billing → Budgets)"
fi

cat > "$REPO/ops/server.env" <<ENV
# written by ops/oci/provision.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ); read by podcast/pod.py deploy
PODCAST_HOST=ubuntu@$PUBIP
PODCAST_INSTANCE_OCID=$INSTANCE
PODCAST_RESERVED_IP_OCID=$PUBIP_ID
PODCAST_VCN_OCID=$VCN
ENV
say "done. server: ubuntu@$PUBIP   (ssh -i .secrets/podcast_server_key ubuntu@$PUBIP)"
say "DNS: podcast.age-of-abundance.org and podcast.cocreations.com.au -> A $PUBIP (ops/DNS.md)"
