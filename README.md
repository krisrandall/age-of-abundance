# Age of Abundance

A world where everyone has the basics. In the age of AI, far more is possible — this project
is the public home for the practical pieces of that:

1. **Open Government** — publicly declare the world you want and the priorities you hold, so
   anyone can check whether the laws you support actually match. A foundation for a truth era.
2. **The Affordable Housing Company** — a group pools cash to buy a rental home outright (no
   debt) through a shared company + unit trust, opening property to ordinary people and taking
   a home out of the speculative market.
3. **The podcast** — conversations on the way there. First episodes 2027.

Site: https://age-of-abundance.org (until the domain is switched on, https://krisrandall.github.io/age-of-abundance/).

## Map

- `site/` — the Astro site. All the words live in plain Markdown under `site/src/pages/`.
  Deployed to GitHub Pages by `.github/workflows/deploy.yml` on every push to `main`.
- `podcast/` — the podcast service: two shows (`shows/age-of-abundance`, and the preserved
  archive of *The Unfinished Cubby* in `shows/unfinished-cubby`), one script (`pod.py`) that
  builds each show's RSS feed and pages and puts them on our own server. See `podcast/FORMATS.md`.
- `ops/` — the server (Oracle Cloud, Caddy), DNS records, the runbooks. Kris-only.
- `release/` — reserved for a later helper that turns a recording into a released episode.
- `WHY.md` → `CLAUDE.md` → `DECISIONS.md` — read in that order before changing anything.

## Run it locally

```bash
# the site
cd site && npm install && npm run dev        # http://localhost:4321/

# the podcast feeds
cd podcast && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python pod.py build && .venv/bin/python pod.py check && .venv/bin/python pod.py serve
```
