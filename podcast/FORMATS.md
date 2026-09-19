# Formats — the contract for everything in `shows/`

`pod.py` reads these files fresh on every build and stores nothing else. Any person or AI may
edit them by hand. Unknown keys are kept as they are. Changing a format means migrating every
existing file in the same commit and updating this file.

## A show — `shows/<show>/`

```
show.yaml        the show's settings (below)
episodes/        one file per episode: epNN-<slug>.html
art/             cover.jpg and one image per episode, square JPEG/PNG 1400–3000 px. In git.
media/           the mp3s. NOT in git (.gitignore). The laptop and the server hold them.
import/          (archives only) the feed the show was imported from; `check` proves the
                 GUIDs, titles and numbers still match it. Delete it to stop that check.
```

`<show>` is lowercase letters, digits and hyphens. It is also the folder under `public/` and,
by default, under `site/public/` where `deploy` puts the built feed and pages.

## `show.yaml`

```
title: Age of Abundance
site_url: https://krisrandall.github.io/age-of-abundance/podcast   # the feed is <site_url>/feed.xml; pages under it. PERMANENT.
audio_base_url: https://github.com/krisrandall/age-of-abundance/releases/download/audio-age-of-abundance
                                         # where the mp3s are fetched from (a GitHub release: no server).
                                         # Omit it to serve them from <site_url>/media/ on a server of our own.
audio_release: audio-age-of-abundance    # the release tag `deploy` uploads to
index_page: false                        # true (default) writes index.html; false when the site has its own page
publish_dir: site/public/podcast         # optional, relative to the repo root; default site/public/<show>/
status: prelaunch                        # prelaunch | live | archive — a note to humans; archive
                                         #   also means "no new episodes" (check enforces it)
description: |                           # plain text; blank line = new paragraph
  …
language: en
copyright: Kris Randall 2026
license: Kris Randall 2026
author: Kris Randall
owner_name: Kris Randall
owner_email: ""                          # empty = no <itunes:email>; set it when a directory asks
explicit: false
type: episodic                           # episodic | serial
medium: podcast
guid: 5f3e…                              # the show's identity across hosts. NEVER change.
locked: true                             # <podcast:locked>yes</podcast:locked> (true/false, not yes/no)
categories:                              # Apple's list; [main, sub] or [main]
  - [Society & Culture, Philosophy]
  - [Government]
cover: cover.jpg                         # in art/
home_url: https://age-of-abundance.org/  # the "← back" link on the pages
home_label: Age of Abundance
status_note: First episodes 2027.        # shown under the description; may be empty
apple_url: …                             # subscribe buttons: any of apple_url, spotify_url,
spotify_url: …                           #   pocketcasts_url, amazon_url, youtube_url; RSS is
old_feed_url: …                          #   always added. old_* are for archives (cutover checks).
old_site_url: …
```

## An episode — `shows/<show>/episodes/epNN-<slug>.html`

`NN` is the episode number, two digits or more. `<slug>` is the title before the last
` - `, lowercased, runs of anything but a-z 0-9 turned into one hyphen, at most 60 chars.
The mp3 and the episode art share the stem (`epNN-<slug>.mp3`, `.jpg`). **Never rename a
file after it has been deployed** — the URLs are permanent. Sort order is by episode
number, never by file name.

```
---
title: Work life balance just means lazy - Jeff Mustard   # exactly as shown in apps
guest: Jeff Mustard              # pages only
episode: 1
season: 1
type: full                       # full | trailer | bonus
guid: 6cd910b2-…                 # NEVER edit. Imported verbatim; uuid4 for new episodes.
pubdate: '2021-03-26T23:37:51+00:00'   # ISO 8601 with offset; the feed shows it in GMT
audio: ep01-work-life-balance-just-means-lazy.mp3   # in media/
image: ep01-work-life-balance-just-means-lazy.jpg   # in art/; empty = the cover is used
youtube: ''                      # optional link, pages only
explicit: false
draft: false                     # true = left out of the build (kept in git)
rsscom_url: https://…            # provenance for imported episodes; ignored otherwise
---
<p>The description, as HTML. Apps keep only: p, a, ul, ol, li, em, strong, br.</p>
```

Derived at build and never stored: the enclosure `length` (the mp3's size), its `type`
(`audio/mpeg` — only .mp3 is served), `itunes:duration` (ffprobe), the item `link`
(`<site_url>/episodes/<slug>/`) and the media (`<audio_base_url>/<file>`) and art URLs.

`check` refuses: a description that is empty or still holds `[Kris:`; more than 4000
characters; tags outside the list above; a duplicate guid or episode number; a pubdate in
the future; art that is not square, not 1400–3000 px, not JPEG/PNG, not RGB; a missing mp3;
and, for a show with `import/`, any difference in GUIDs, titles or numbers from the old feed.
