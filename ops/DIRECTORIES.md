# Listing a show in the podcast directories — notes

What each directory asks for, gathered while moving The Unfinished Cubby. Useful if the Age
of Abundance show ever has episodes and wants listing; nothing here is scheduled.

- Cover art: square, 1400–3000 px (3000 recommended), JPEG or PNG, RGB. `pod.py check`
  proves the shape. The Age of Abundance cover in git is a generated placeholder.
- `owner_email` in `show.yaml`: Spotify and Amazon send a verification code there. It can be
  emptied again after the claim; the tag is omitted when empty.
- At least one episode in the feed before submitting. A short `type: trailer` counts.
- `pod.py check --show <show> --live` green; https://castfeedvalidator.com and
  https://podba.se/validate are the two public validators (both are forms).
- Where to submit: Apple Podcasts Connect (https://podcastsconnect.apple.com, + → New show →
  RSS feed), Spotify for Creators (https://podcasters.spotify.com, "I have a podcast"),
  Amazon Music for Podcasters (https://podcasters.amazon.com), Pocket Casts
  (https://pocketcasts.com/submit), iHeart (https://podcasters.iheart.com), Podcast Index
  (https://podcastindex.org/add — feeds on Apple usually appear by themselves). Each gives a
  share URL that goes into `show.yaml` (`apple_url`, `spotify_url`, `pocketcasts_url`,
  `amazon_url`, `youtube_url`); the subscribe buttons come from those.
- `status: live` and a `status_note` in `show.yaml` once listed.
