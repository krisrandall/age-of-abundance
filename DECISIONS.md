# Decisions

Append-only. Newest at the bottom. Date, decision, why, in three to five lines. A decision
is not re-litigated quietly: to reverse one, add a new entry that says so.

## 2026-09-14 — One repo: `site/` + `podcast/` + `ops/`
The Astro site moved from the repo root into `site/` (history kept with `git mv`; the Pages
workflow builds with `path: ./site`). The podcast service lives beside it in `podcast/`, the
server and DNS in `ops/`, a future release helper in `release/`. Pattern from Land of Lor: one
repo holds everything about one project.

## 2026-09-14 — Own the feeds; static files on a free-tier Oracle server
Two shows, one mechanism: plain episode files → `pod.py build` → `feed.xml` + pages → rsync →
Caddy. Not rss.com (annual fee, feed hostage to the subscription), not Byethost/iFastNet (its
terms forbid HTTP download of audio and the business site shares the account), not the Land
of Lor droplet (Kris's call: keep projects on separate machines). Oracle Always Free with the
account on Pay As You Go, so the idle-reclaim rule cannot stop the server; $0 inside limits.

## 2026-09-14 — Two permanent feed URLs
`https://podcast.age-of-abundance.org/feed.xml` for the new show and
`https://podcast.cocreations.com.au/feed.xml` for The Unfinished Cubby archive (a
CoCreations-era show keeps a CoCreations address). One Caddy host block each, same server.
Reversing either means a 301 from the old address forever; do not.

## 2026-09-14 — The Unfinished Cubby is preserved, then cut over before December 2026
Imported verbatim from the public rss.com feed (GUIDs, descriptions, art, audio). rss.com is
paid until April 2027 and its redirect only works while the account is active, so the
redirect to our feed must be placed by December 2026 (`ops/CUTOVER-unfinished-cubby.md`).

## 2026-09-14 — Dependencies: pyyaml only (podcast); astro (site)
`podcast/pod.py` is stdlib + PyYAML, shelling out to curl, ffprobe, identify, rsync, xmllint.
Not python-frontmatter, not a markdown library (descriptions are HTML, as rss.com's were), not
feedgen (string assembly gives byte-for-byte control over CDATA and tag order). Adding
anything is a new entry here.

## 2026-09-14 — The new show's cover art is a placeholder
`podcast/shows/age-of-abundance/art/cover.jpg` is generated (Pillow, the site's colours and
wordmark) so the pipeline runs end to end. It is replaced with real art before the show is
submitted to any directory (`ops/LAUNCH-age-of-abundance.md`).

## 2026-09-19 — No server: GitHub Pages for the feeds, GitHub Releases for the audio
Reverses the Oracle decision of 2026-09-14 (Kris: "oracle is not playing nice"; parked). A feed
needs only a static file and permanent, range-capable mp3 URLs; Pages gives the first, a
release's assets the second (2 GB each, no sign-up, no card, no idle rule). Not SoundCloud
(3 free hours, no stable direct URLs, its own feed = lock-in again). Feed addresses are the
github.io ones for good; a custom domain later adds a 301 on top. If GitHub ever objected to
the traffic (a few downloads a day), `audio_base_url` moves the files and the feed URL stays.

## 2026-09-19 — Two feed addresses, both under the site
`https://krisrandall.github.io/age-of-abundance/podcast/feed.xml` and
`…/age-of-abundance/unfinished-cubby/feed.xml`. Reverses the 2026-09-14 "two permanent feed
URLs" entry: with no server there is no `podcast.` subdomain, and Kris does not care about
the domain names now. The old rss.com feed will 301 to the Cubby one (cutover doc).

## 2026-09-19 — The Unfinished Cubby has moved; Age of Abundance the show is an idea for one day
Kris placed the rss.com redirect the same day the new feed went live (verified 301; record in
`ops/UNFINISHED-CUBBY-MOVE.md`), so the December 2026 deadline of the 2026-09-14 entry is met
and gone. The first Age of Abundance conversation (with Simon) was published standalone on
SoundCloud and Medium, not as an episode; the show's feed stays empty and unlisted until the
show exists. The docs carry records and notes now, not schedules.
