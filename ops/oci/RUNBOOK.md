# The podcast server — runbook

One Oracle Cloud Always Free instance (`podcast-server`, `VM.Standard.E2.1.Micro`, Ubuntu
24.04, 50 GB), a reserved public IP, one VCN. Everything was made by `provision.sh`, which
can be rerun safely. Facts live in `ops/server.env`; secrets in `.secrets/` (gitignored).

    export OCI_CLI_CONFIG_FILE=~/Dev/age-of-abundance/.secrets/oci/config
    OCI=~/.local/bin/oci          # installed with `uv tool install oci-cli`
    source ops/server.env         # PODCAST_HOST, PODCAST_INSTANCE_OCID, PODCAST_RESERVED_IP_OCID, PODCAST_VCN_OCID

## Everyday

    ssh -i .secrets/podcast_server_key $PODCAST_HOST            # log in
    ops/oci/provision.sh --status                                # is it running, what shape, where
    ssh -i .secrets/podcast_server_key $PODCAST_HOST 'systemctl status caddy --no-pager; sudo journalctl -u caddy -n 30 --no-pager'
    ssh -i .secrets/podcast_server_key $PODCAST_HOST 'df -h / ; du -sh /var/www/podcast/*'
    cd podcast && python3 pod.py check --live                    # the feeds as the world sees them

First boot takes a few minutes (packages, Caddy). `/var/www/podcast/.cloud-init-done` exists
when it has finished; `sudo cat /var/log/cloud-init-output.log` shows what happened.

## Changing the Caddyfile

Edit `ops/Caddyfile`, then:

    scp -i .secrets/podcast_server_key ops/Caddyfile $PODCAST_HOST:/tmp/Caddyfile
    ssh -i .secrets/podcast_server_key $PODCAST_HOST 'sudo caddy validate --config /tmp/Caddyfile && sudo cp /tmp/Caddyfile /etc/caddy/Caddyfile && sudo systemctl reload caddy'

## Certificates

Caddy gets them from Let's Encrypt on its own once a hostname resolves to this IP and ports
80/443 are open (the security list and the OS firewall both — cloud-init did both). Watch:
`sudo journalctl -u caddy -f`. If a name was added to the Caddyfile before its DNS existed,
Caddy just retries; nothing to do.

## The first Cubby media load (done once; kept for a rebuild)

The 1.66 GB came from rss.com straight to the server, not up the AU uplink:

    scp -i .secrets/podcast_server_key podcast/pod.py podcast/shows/unfinished-cubby/import/*.xml $PODCAST_HOST:/tmp/
    ssh -i .secrets/podcast_server_key $PODCAST_HOST 'sudo apt-get install -y ffmpeg >/dev/null; python3 /tmp/pod.py import-media-only --from /tmp/feed-*.xml --dest /var/www/podcast/unfinished-cubby'
    cd podcast && python3 pod.py deploy --show unfinished-cubby   # rsync then only reconciles

## Stop / start / rebuild

    $OCI compute instance action --instance-id $PODCAST_INSTANCE_OCID --action STOP  --wait-for-state STOPPED
    $OCI compute instance action --instance-id $PODCAST_INSTANCE_OCID --action START --wait-for-state RUNNING
    # rebuild from nothing: terminate (below), then `ops/oci/provision.sh` — the reserved IP and
    # the VCN survive, DNS keeps pointing at the same address, then `pod.py deploy` refills it.

## Backups

The mp3s are on the laptop and here. A boot-volume backup is a third copy (5 are free):

    BV=$($OCI compute boot-volume-attachment list -c $(sed -n 's/^tenancy *= *//p' $OCI_CLI_CONFIG_FILE) --instance-id $PODCAST_INSTANCE_OCID --availability-domain "$($OCI compute instance get --instance-id $PODCAST_INSTANCE_OCID --query 'data."availability-domain"' --raw-output)" --query 'data[0]."boot-volume-id"' --raw-output)
    $OCI bv boot-volume-backup create --boot-volume-id $BV --display-name "podcast-$(date +%Y%m%d)" --type FULL

## If Oracle emails

- "Idle compute instance will be reclaimed": the account is not on Pay As You Go. Fix that
  (ops/SETUP.md step 2). A stopped instance is restarted with the START action above; the
  files and the IP survive a stop.
- "Exceeds Always Free limits": we run one E2.1.Micro and one reserved IP; check
  `provision.sh --status` and the Billing → Cost analysis page.
- Budget alert (AU$1 forecast): look at Billing → Cost analysis before anything else.

## Tearing it all down

In this order, from the laptop (everything is tagged `project=age-of-abundance`):

    $OCI compute instance terminate --instance-id $PODCAST_INSTANCE_OCID --preserve-boot-volume false --force
    $OCI network public-ip delete --public-ip-id $PODCAST_RESERVED_IP_OCID --force
    # then the subnet, internet gateway and VCN (the VCN delete needs the others gone first):
    $OCI network subnet delete --subnet-id "$($OCI network subnet list -c <compartment> --vcn-id $PODCAST_VCN_OCID --query 'data[0].id' --raw-output)" --force
    $OCI network internet-gateway delete --ig-id "$($OCI network internet-gateway list -c <compartment> --vcn-id $PODCAST_VCN_OCID --query 'data[0].id' --raw-output)" --force
    $OCI network vcn delete --vcn-id $PODCAST_VCN_OCID --force
    # the budget: Billing → Budgets → podcast-budget → delete. The API key: Profile → User settings → API keys.

Delete the two `podcast` A records afterwards, and `ops/server.env`.
