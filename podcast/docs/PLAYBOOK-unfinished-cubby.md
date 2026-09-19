# The Unfinished Cubby — the old release playbook (2021–2023)

Kris's own notes on how an episode was made and published while the show was on rss.com.
Kept verbatim (lightly formatted) because `release/` will one day automate the same steps,
and because the "where the show is listed" table below is what the cutover has to carry.
The rss.com steps no longer apply; the feed now comes from `pod.py` (see `../FORMATS.md`).

## Recording

Usually recorded on Angel's phone, which uploads to Google Photos; partner sharing makes it
available to Kris, who "saves" it into his own photos and downloads it to the computer.

## Making the episode video and audio

All the intro assets are in the Google Drive folder *Intro Assets*. Editing is in iMovie;
usually all that is done is:

1. Make the intro screen image — there is a GIMP file for it in the assets folder. Open it,
   change the text below the line to the episode name (*"Title" with guest name*, e.g.
   *Work life balance just means lazy* with Jeff Mustard). Shrink a copy with
   https://squoosh.app/ for later use as the thumbnail.
2. Start a new iMovie project and load four assets:
   - A. the title image just made, shown for one second with the default "Ken Burns" zoom,
     at the very start;
   - B. the opening sequence video;
   - C. the opening sequence theme (drag its volume below the median line);
   - D. the interview video just recorded.
   B and C go together directly after A, and C fades into D.
3. Habit: start the recording before the interview officially starts (the official start is
   "Welcome to the Unfinished Cubby Podcast, I'm speaking with …"); the preamble conversation
   goes at the very end of the recording, after a 12-second blank gap after the interview.
4. Select everything and File → Share → YouTube to export the video; File → Share → File,
   Format: Audio Only, for the audio. The exports take about an hour.

## Upload the video

If the video is too big, use Handbrake to resize it to something the NBN can upload.
The exported `.mov` goes to YouTube on the cocreations.education@gmail.com account
(password in 1Password), channel *The Unfinished Cubby Podcast*:
https://www.youtube.com/channel/UCoIaiJMA2bIzL773vV8i-yw

- UPLOAD VIDEO, drag the file over.
- Name it like *Work/Life balance just means lazy . The Unfinished Cubby . Episode 01 . Jeff Mustard*.
- Upload the title image as the thumbnail.
- Description: what the episode is about, what was discussed, and a link to the podcast site.

Example:

> In this very first episode of The Unfinished Cubby podcast, Kris talks with Jeff Mustard on
> the theme of "Work life balance just means lazy". We explore meaning making and solid
> techniques for planning a good life in the context of family and work.
> This episode was actually filmed on location in the cubby house which inspires the podcast.

## Upload the audio (was rss.com; now `pod.py`)

Then: rss.com dashboard → + New episode → thumbnail as the episode art, season 1 and the
episode number, title *(topic) - (guest)*, the exported audio, Schedule or Publish now.
Now: `python3 pod.py new --show unfinished-cubby …` — but the show is an archive; see
`../../CLAUDE.md`.

## Post on social media

A Facebook post to the video, plus a link to the podcast site and "search for The Unfinished
Cubby in your podcast app".

## Where the show is listed

The rss.com feed was `https://media.rss.com/unfinishedcubby/feed.xml`; the new one is
`https://krisrandall.github.io/age-of-abundance/unfinished-cubby/feed.xml` (see `../../ops/UNFINISHED-CUBBY-MOVE.md`).

| Directory | Account | Share URL |
|---|---|---|
| Apple Podcasts | kris.randall@gmail.com Apple ID, https://podcastsconnect.apple.com | https://podcasts.apple.com/au/podcast/the-unfinished-cubby/id1560437668 |
| Spotify | signed up with Facebook, https://podcasters.spotify.com | https://open.spotify.com/show/3yzUfgj77WO2DHue10B0lV |
| Pocket Casts | https://www.pocketcasts.com/submit/ | https://pca.st/ptrvpxg3 |
| Amazon Music | | https://music.amazon.co.uk/podcasts/501c9299-3a14-4d4d-a3c3-789908e7e0f5 |
| iHeartRadio | kris.randall@gmail.com, https://podcasters.iheart.com/ | https://www.iheart.com/podcast/85332895/ |
| Podbean | kris.randall@gmail.com | https://www.podbean.com/podcast-detail/z3iar-1b6e82/The-Unfinished-Cubby-Podcast |
| Player FM | | https://player.fm/series/the-unfinished-cubby |
| TuneIn | submitted by form | https://tunein.com/podcasts/Philosophy-Podcasts/The-UnfinishedCubby-p1485000/ |
| Google Podcasts | cocreations.education@gmail.com | service closed 2024 |
| Stitcher | | service closed 2023 |
| IMDb | submitted, never confirmed | — |

Other: Patreon https://www.patreon.com/unfinishedcubby (unused); Podcorn (kris.randall@gmail.com).
