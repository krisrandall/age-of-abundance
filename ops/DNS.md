# DNS — every record, where it lives, and why

Two zones, two panels, both Kris's. Add the records after `ops/oci/provision.sh` has printed
the reserved IP (it is also in `ops/server.env`). Check each with
`dig +short <name> @8.8.8.8`.

## age-of-abundance.org — Namecheap (Domain List → Manage → Advanced DNS)

Delete the parking records Namecheap put there, then add:

| Type  | Host      | Value                      | Why |
|-------|-----------|----------------------------|-----|
| A     | `@`       | `185.199.108.153`          | GitHub Pages, the site |
| A     | `@`       | `185.199.109.153`          | " |
| A     | `@`       | `185.199.110.153`          | " |
| A     | `@`       | `185.199.111.153`          | " |
| AAAA  | `@`       | `2606:50c0:8000::153`      | " (IPv6) |
| AAAA  | `@`       | `2606:50c0:8001::153`      | " |
| AAAA  | `@`       | `2606:50c0:8002::153`      | " |
| AAAA  | `@`       | `2606:50c0:8003::153`      | " |
| CNAME | `www`     | `krisrandall.github.io.`   | www → the site |
| A     | `podcast` | *the reserved IP*          | the feeds and audio, our Oracle server |

TTL: Automatic. GitHub's addresses are the ones in its docs; if they ever change, the Pages
settings page says so.

## cocreations.com.au — iFastNet cPanel (Zone Editor)

| Type | Name                          | Value             | Why |
|------|-------------------------------|-------------------|-----|
| A    | `podcast.cocreations.com.au.` | *the reserved IP* | The Unfinished Cubby archive feed |

Nothing else in that zone changes; the business site stays where it is.

## Then

- The session runs `podcast/pod.py check --live` for both shows; Caddy on the server
  fetches its certificates the first time each name resolves (`ops/oci/RUNBOOK.md` shows
  how to watch that).
- The site's domain switch is step 3 of `ops/SETUP.md`.
