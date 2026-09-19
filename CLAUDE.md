# Age of Abundance — how to work here

Read `WHY.md` first. This file is a router: what lives where, who may change what, and the
procedure for a session. Keep it under 80 lines.

## What this is
Kris's public project: a small Astro site (https://krisrandall.github.io/age-of-abundance/,
age-of-abundance.org later) and a podcast service with no server at all — feeds and pages on
GitHub Pages, mp3s as GitHub Release assets — serving two shows: the new *Age of Abundance*
show (`…/age-of-abundance/podcast/feed.xml`, launching 2027) and the preserved archive of
*The Unfinished Cubby* (`…/age-of-abundance/unfinished-cubby/feed.xml`, 18 episodes, 2021–2023).

## Map
- `site/` — Astro 4. Words are Markdown under `site/src/pages/`; frontmatter (`title`, `lede`,
  `pillar`, `section`) drives headings and sub-nav; the pillar map is in
  `site/src/layouts/BaseLayout.astro`, the top nav in `site/src/components/Nav.astro`.
  Pushed to `main` → live on GitHub Pages in about a minute.
- `podcast/` — the feed service. `pod.py` is the whole tool (`import | new | build | check |
  deploy | serve`, each with `--show`). `shows/<show>/show.yaml` + `episodes/*.html` +
  `art/` are the content; `media/` (the mp3s) is on disk and on the show's GitHub release,
  never in git. The contract is `podcast/FORMATS.md`. `build` writes `podcast/public/`
  (ignored); `deploy` uploads new mp3s to the release, copies the feed and pages into
  `site/public/<show>/` (committed — that is how they publish) and pushes.
- `ops/` — the runbook (where things live, how to move them), the Cubby cutover and the
  2027 launch checklist. No secrets anywhere: `gh` is signed in on the laptop.
- `release/` — placeholder for the later recording-to-release helper. Nothing there yet.
- `DECISIONS.md` — append-only.

## Rules (each carries the incident it came from)
1. A published feed URL, episode URL, media filename or `guid:` never changes. Apple and
   Spotify key episodes on the GUID; a changed one shows every listener a duplicate.
2. Media is never committed to git. `podcast/shows/*/media/` is 1.7 GB and grows; git would
   choke. The laptop and the GitHub release are the copies (`deploy` keeps the release complete).
3. A release asset is never replaced or renamed (`deploy` refuses): its URL is in every
   listener's app. A fixed recording is a new file name and a new episode file.
4. `pod.py check` must pass before `deploy`, and `deploy` runs it. It refuses `[Kris:`
   placeholders, so a half-written episode cannot ship.
5. No server. Files on GitHub Pages and GitHub Releases; nothing to keep alive.
   (2026-08-10/11/12: three long-lived watchers died silently on the task-runner host;
   2026-09-19: the Oracle free tier would not cooperate and was parked.)
6. Pinned dependencies; adding one needs a `DECISIONS.md` entry. (2026-08-10: an unpinned
   MCP library broke every container on the task-runner platform in one rebuild.)
7. Kris's words. Site copy, show descriptions and episode notes are his; placeholders look
   like `[Kris: what goes here]`. Draft from his existing words when asked, say so, and flag it.
8. Never touch a podcast directory (Apple, Spotify, rss.com) without Kris. Those clicks are
   his, and they are in `ops/CUTOVER-unfinished-cubby.md` and `ops/LAUNCH-age-of-abundance.md`.
9. `WHY.md` ≤ 40 lines, this file ≤ 80. Words here are paid for by every future session.

## A session (any agent: laptop, task runner, or otherwise)
1. `git pull` first. Read `WHY.md`, then this file, then `podcast/FORMATS.md` before
   touching `podcast/shows/`.
2. Do what the request says, literally. Do not decompose it into a project.
3. Site change: `cd site && npm run build` must pass. Podcast change: `cd podcast &&
   python3 -m unittest && python3 pod.py check` must pass.
4. Commit as you go: `site: …`, `podcast: …`, `ops: …`, `docs: …`. A session never ends
   with uncommitted work. Never force-push.
5. Push. The site deploys itself; a feed changes only when someone runs `pod.py deploy`
   (which commits `site/public/<show>/` and pushes).
6. Reply in plain words with the link to what changed.

## Releasing an episode (Kris, from the laptop)
    cd podcast
    python3 pod.py new --show age-of-abundance --mp3 ~/path/to/recording.mp3 \
        --title "Topic - Guest Name" --guest "Guest Name"      # prints the file to edit
    # write the description in that file, then:
    python3 pod.py deploy --show age-of-abundance      # builds, checks, uploads, publishes, checks live
