# The Unfinished Cubby — moving the listeners from rss.com to our feed

**Deadline: December 2026.** rss.com is paid until April 2027 and its redirect only works
while the subscription is active; directories need weeks to follow a redirect. Nothing else
about this is urgent, and nothing here is undone easily, so one step at a time.

Old feed: `https://media.rss.com/unfinishedcubby/feed.xml`
New feed: `https://podcast.cocreations.com.au/feed.xml`

## Before touching rss.com (the session does these)

1. `cd podcast && python3 pod.py check --show unfinished-cubby --live` is green: 18
   episodes, every GUID, title and number identical to the copy of the old feed in
   `shows/unfinished-cubby/import/`, every mp3 the same size as rss.com's, byte ranges
   working.
2. The feed passes both public validators with no errors:
   https://castfeedvalidator.com and https://podba.se/validate
3. Kris subscribes by URL in Pocket Casts (Discover → search box → paste the URL) and in
   Apple Podcasts (Library → … → Follow a Show by URL), sees 18 episodes with art, plays
   one and drags the slider to the middle. That last bit proves range requests.

## The redirect (Kris, in the rss.com dashboard)

4. https://dashboard.rss.com/podcasts/unfinishedcubby/settings/ → **Copy Protection →
   Disable Protection** (it must be off before a redirect).
5. Same page → **Redirect My Podcast** → paste `https://podcast.cocreations.com.au/feed.xml`
   → **Redirect my show**.
6. Never click **Delete my podcast**. Never publish an episode on rss.com again. Leave the
   subscription alone; it lapses in April 2027 by itself.

## After (the session checks; Kris clicks where noted)

7. `curl -sI https://media.rss.com/unfinishedcubby/feed.xml` returns `301` with the new
   address. Old episode URLs on content.rss.com keep working while the account lives, which
   is what already-downloaded episodes in people's apps need.
8. Within a day or two, https://podcastindex.org (search "Unfinished Cubby") shows the new
   feed URL — the cheapest proof the redirect is being followed.
9. **Apple**: https://podcastsconnect.apple.com → the show → the RSS feed URL should read the
   new address within a week. If it does not, **Kris** clicks Edit beside it and pastes the
   new URL. Apple accepts it because the GUIDs match, so no episode is duplicated.
10. **Spotify**: https://podcasters.spotify.com → the show → Settings → RSS feed → **Update**
    → paste the new URL → Submit. **Kris** does this by hand now rather than waiting.
11. Amazon Music, iHeart, Pocket Casts, Podbean, Player FM, TuneIn follow the 301. Check
    each listing (links in `podcast/docs/PLAYBOOK-unfinished-cubby.md`) after a week; if one
    is stale, its "update feed" page or support email is the fix. Google Podcasts and
    Stitcher no longer exist.
12. Later, separately: the episode descriptions still link to
    `https://rss.com/podcasts/unfinishedcubby/`, which dies with the account. Replacing
    those links with `https://podcast.cocreations.com.au/` is one commit; it changes the
    words listeners see, so it is Kris's call.

## Never

Edit a `guid:`; rename a published mp3; delete the podcast on rss.com or on Apple; place
the redirect before step 3 has passed.
