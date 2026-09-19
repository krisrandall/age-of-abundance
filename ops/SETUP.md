# Setup — what only Kris can do

Nothing is needed to run the podcast: GitHub Pages and GitHub Releases are already on, and
`podcast/pod.py deploy` from the laptop does the rest (it needs `gh` signed in, which it is).

Left for Kris, when he wants:

1. **The Unfinished Cubby cutover** — `ops/CUTOVER-unfinished-cubby.md`. The rss.com redirect
   must be placed **before December 2026**; the new feed is live now.
2. **The 2027 launch** of the Age of Abundance show — `ops/LAUNCH-age-of-abundance.md`.
3. **The site's own domain** (age-of-abundance.org, bought, parked) — `ops/RUNBOOK.md`,
   "A custom domain later". Optional; the github.io addresses work indefinitely.
4. **A copy of the audio for posterity** — the Internet Archive, see `ops/RUNBOOK.md`.
5. **Publishing from the AI Task Runner** — a checkout there with `gh` signed in; nothing
   secret lives in the repo, so there is no `.secrets/` to copy any more.
