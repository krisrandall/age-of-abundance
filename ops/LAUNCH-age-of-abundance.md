# Age of Abundance — putting the show in the directories (2027)

The feed is live from the first deploy at `https://krisrandall.github.io/age-of-abundance/podcast/feed.xml`,
just not listed anywhere. Episodes can be published to it at any time (`pod.py new` →
`build` → `check` → `deploy`) and the page link shared. Listing it is a separate, one-day
job, once:

## Before submitting

- [ ] Real cover art in `podcast/shows/age-of-abundance/art/cover.jpg`: square, 3000×3000
      recommended (1400 minimum), JPEG or PNG, RGB, under 512 KB is kind to apps. The
      placeholder there now is generated. `pod.py check` proves the size and shape.
- [ ] The description and categories in `show.yaml` are Kris's final words. Apple's
      category list: https://podcasters.apple.com/support/1691-apple-podcasts-categories
- [ ] `owner_email` set in `show.yaml` (Spotify and Amazon send a verification code there),
      then `build` + `check` + `deploy`. It can be emptied again after the claims.
- [ ] At least one episode in the feed. A short `type: trailer` counts and is common.
- [ ] `pod.py check --show age-of-abundance --live` green; both validators clean
      (https://castfeedvalidator.com, https://podba.se/validate).

## Submit (Kris; each takes minutes, approval takes hours to days)

- [ ] Apple Podcasts Connect — https://podcastsconnect.apple.com → + → New show → RSS feed.
      Share URL arrives when approved; put it in `show.yaml` as `apple_url`.
- [ ] Spotify for Creators — https://podcasters.spotify.com → Get started → "I have a
      podcast" → feed URL → the emailed code. `spotify_url`.
- [ ] Amazon Music for Podcasters — https://podcasters.amazon.com. `amazon_url`.
- [ ] Pocket Casts — https://pocketcasts.com/submit. `pocketcasts_url`.
- [ ] iHeart — https://podcasters.iheart.com. YouTube (if the video versions go there):
      `youtube_url`.
- [ ] Podcast Index — https://podcastindex.org/add. Feeds submitted to Apple usually appear
      by themselves.

Then `build` + `deploy`: the subscribe buttons on the show's page come from those keys, and
the site's podcast page (`site/src/pages/podcast/index.md`) gets the same links.

## After

Set `status: live` in `show.yaml` and `status_note` to whatever the page should say (or
empty). Record the date here.
