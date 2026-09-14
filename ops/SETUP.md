# Setup — the steps only Kris can do, and what happens after each

## 1. Oracle Cloud (once)

1. Sign in at https://cloud.oracle.com with kris.randall@gmail.com. Note the **tenancy name**
   and the **home region** (top right; Sydney expected). If the tenancy is gone (Oracle
   removes long-idle free accounts), sign up again — on another email if it refuses the old
   one — and choose **Sydney** as the home region; Always Free lives only there.
2. **Billing → Upgrade and Manage Payment → Pay As You Go.** A card goes on file; nothing is
   charged while usage stays inside the Always Free limits (this server uses a fraction of
   them). It is the documented way to stop Oracle stopping an "idle" server, and a static
   feed server is idle by their measure (CPU and network under 20% for 7 days).
3. **Profile menu (top right) → User settings → API keys → Add API key.** Choose *Generate
   API key pair*, click **Download private key**, then **Add**. Copy the **Configuration
   File Preview** that appears. Then, on the laptop:

        mkdir -p ~/Dev/age-of-abundance/.secrets/oci
        mv ~/Downloads/*.pem ~/Dev/age-of-abundance/.secrets/oci/oci_api_key.pem
        # paste the preview into ~/Dev/age-of-abundance/.secrets/oci/config and set the last line to:
        # key_file=/home/krisrandall/Dev/age-of-abundance/.secrets/oci/oci_api_key.pem
        chmod 600 ~/Dev/age-of-abundance/.secrets/oci/*

   Put copies of both files in 1Password ("Oracle Cloud API key — age-of-abundance").
   `.secrets/` is gitignored; `pod.py check` fails if it ever gets tracked.
4. Tell the session. It then runs `ops/oci/provision.sh`: lists what already exists in the
   tenancy (old instances from 2020/2024 may be there — **it asks before terminating any**),
   creates the network, a reserved IP, the instance, a AU$1 budget alert, and prints the IP.

## 2. DNS (once, after step 1 has printed the IP) — see `ops/DNS.md`

## 3. The site's domain (once, after the DNS records exist)

Done by the session with `gh api` and one commit, in this order, so nothing is ever down:
1. `gh api -X PUT repos/krisrandall/age-of-abundance/pages -f cname=age-of-abundance.org`
2. `site/astro.config.mjs`: `site: 'https://age-of-abundance.org'`, `base: '/'`;
   `site/public/CNAME` = `age-of-abundance.org`; the README's local URL. Push.
3. When https://age-of-abundance.org answers with a certificate (GitHub issues it within
   the hour): `gh api -X PUT repos/krisrandall/age-of-abundance/pages -F https_enforced=true`.
   The old github.io address redirects to the new one from then on.

## 4. Later, whenever

- `ops/CUTOVER-unfinished-cubby.md` — the rss.com redirect. **Before December 2026.**
- `ops/LAUNCH-age-of-abundance.md` — submitting the new show to the directories, 2027.
- A copy of `.secrets/` on the AI Task Runner's checkout, so `pod.py deploy` works there.
