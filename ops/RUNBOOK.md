# Runbook — where everything lives and how to move it

No server. Two free GitHub services carry the podcast:

- **GitHub Pages** serves the site (`site/`, built by `.github/workflows/deploy.yml` on every
  push to `main`). Each show's feed and pages are plain files under `site/public/<show>/`,
  written there by `podcast/pod.py deploy`, so they publish with the site.
- **GitHub Releases** hold the mp3s: one release per show (`audio-unfinished-cubby`,
  `audio-age-of-abundance`), one asset per episode, uploaded by `pod.py deploy`. Asset URLs
  are permanent: `https://github.com/krisrandall/age-of-abundance/releases/download/<tag>/<file>`.
  A published file is never replaced or renamed (`deploy` refuses). GitHub serves them as
  `application/octet-stream` behind a 302 (verified 2026-09-19: byte ranges work, 206 on a
  range request); podcast apps go by the feed's own `type="audio/mpeg"`, so this is fine.

Addresses (permanent — never change them; a custom domain later gives a 301 from these):

| | feed | pages |
|---|---|---|
| Age of Abundance | https://krisrandall.github.io/age-of-abundance/podcast/feed.xml | the site's `/podcast` page |
| The Unfinished Cubby | https://krisrandall.github.io/age-of-abundance/unfinished-cubby/feed.xml | https://krisrandall.github.io/age-of-abundance/unfinished-cubby/ |

## Everyday

    cd podcast
    python3 pod.py check --live                  # both feeds as the world sees them
    gh release view audio-unfinished-cubby       # what is on a release
    gh run list --limit 3                        # the Pages deploys

## Copies of the audio

1. the laptop: `podcast/shows/<show>/media/` (gitignored);
2. the GitHub release (public);
3. optional, for posterity: the Internet Archive (`pip install internetarchive`, `ia upload`).
   Not done yet; a good idea for an archive show.

## If GitHub ever objects to serving the audio

Unlikely at this audience (a few downloads a day at most), but the recovery is cheap: put the
mp3s anywhere that serves files with byte ranges (Internet Archive, an object store, a small
server), set `audio_base_url` in the show's `show.yaml` to the new base, `pod.py deploy`. The
feed URL does not change, so nobody re-subscribes; already-downloaded episodes are unaffected.

## A custom domain later (optional)

`site/astro.config.mjs` (`site`, `base: '/'`), `site/public/CNAME`, the Pages custom-domain
setting, the DNS records at Namecheap. GitHub then 301-redirects the github.io addresses,
which podcast apps follow — but do it before or well after the rss.com redirect, never the
same week, so only one redirect is settling at a time.
