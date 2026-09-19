# The Unfinished Cubby — how it moved off rss.com (record, September 2026)

Old feed: `https://media.rss.com/unfinishedcubby/feed.xml` (rss.com, 2021–2026).
New feed: `https://krisrandall.github.io/age-of-abundance/unfinished-cubby/feed.xml`.

- **2026-09-14** — the show imported from the public rss.com feed: 18 episodes, GUIDs,
  descriptions and art verbatim, 1.6 GB of audio verified byte-for-byte
  (`podcast/shows/unfinished-cubby/`, the feed copy in `import/`).
- **2026-09-19** — the audio uploaded as assets of the GitHub release `audio-unfinished-cubby`;
  the feed and pages published through GitHub Pages; `pod.py check --live` green (feed
  byte-equal, every enclosure 200 with byte ranges, a range request 206).
- **2026-09-19** — Kris placed the redirect in rss.com's dashboard (Settings → Copy Protection
  off → Redirect My Podcast → the new URL). Verified: the old feed URL answers `301` to the new
  one, and the 18 items come through it.

## How the listings behave from here

Apple Podcasts, Spotify, Pocket Casts, Amazon, iHeart, Podbean, Player FM and TuneIn follow a
301 on their own over days to weeks; Podcast Index (podcastindex.org, search "Unfinished
Cubby") shows the feed URL it currently uses, which is the cheapest way to see it has moved.
Apple Podcasts Connect and Spotify for Creators each have a field for the feed URL that can be
set by hand if a listing ever looks stale. Episodes keyed on GUIDs, and the GUIDs did not
change, so nothing duplicates. The rss.com subscription lapses in April 2027 by itself; the
redirect exists only while rss.com serves it, which is why it was placed now. The old
`content.rss.com` audio links keep working until then, which is what already-downloaded
episodes in people's apps use. Directory links are in
`podcast/docs/PLAYBOOK-unfinished-cubby.md`.

The episode descriptions still link to `rss.com/podcasts/unfinishedcubby/`, which will die
with the account; swapping those links for the new page is one commit, and changes words
listeners see, so it stays Kris's call.
