# Why this exists

Read this before anything else. It sets the order in which trade-offs are decided.

This is Kris's project. Age of Abundance is a public case, made in the open, that in the age
of AI everyone can have the basics — and a few practical pieces that show it: Open Government,
the Affordable Housing Company, and a podcast of conversations along the way. An earlier
podcast, The Unfinished Cubby (2021–2023), is kept here too, so nothing Kris made is lost
when a hosting company's bill comes due.

The system exists so that Kris can, without help from anyone:

1. change any words on the site and see them live within minutes;
2. record a conversation and release it as a podcast episode from one command;
3. know that every episode ever released stays available at the same address, on a server
   he controls, for as long as he wants;
4. hand any part of this to an AI (the task runner, a session like this one) and have it do
   the same thing the same way.

When a choice comes down to it, decide in this order:

1. Permanent addresses. A feed URL or an episode URL, once shared, never changes. If a change
   would move one, it is wrong.
2. Nothing locked inside a service. Every episode, description and setting is a plain file in
   this repo (audio beside it on disk); the server holds only copies. History is the undo.
3. Nothing to keep alive. Static files and a web server, no app process, no cron, no
   database. A thing that does not run cannot die.
4. Free to run. The site is on GitHub Pages, the feeds on a free-tier server. A cost must be
   argued for in `DECISIONS.md`.
5. Kris's time. Assume and proceed on small things; ask when it costs money, cannot be
   undone, is public-facing, or touches a listing in a podcast directory.

What this is not: not a podcast platform, not a CMS, not a place to try frameworks. Growth in
the code is a cost paid by every future session.

The incident this file is built on: in 2026 the annual rss.com bill for a podcast that had
not had a new episode since 2023 came round again, and the only way to stop paying was to
lose the show. The answer was to own the feed.
