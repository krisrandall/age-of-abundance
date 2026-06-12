# Age of Abundance

Public explainers for two practical projects toward a world where everyone has the basics:

1. **Open Government** — publicly declare the world you want and the priorities you hold, so anyone can
   check whether the laws you support actually match. A foundation for a truth era.
2. **The Affordable Housing Company** — a group pools cash to buy a rental home outright (no debt)
   through a shared company + unit trust, opening property to ordinary people and taking a home out of
   the speculative market.

Built as a small [Astro](https://astro.build) static site. All the words live in plain **Markdown**
under `src/pages/` so they're easy to edit and fork.

## Run it locally

```bash
npm install
npm run dev      # http://localhost:4321/age-of-abundance/
```

Other commands:

```bash
npm run build    # static output → dist/
npm run preview  # serve the built dist/ locally
```

## Edit the content

Each page is a Markdown file under `src/pages/`. The page heading, sub-navigation, and "next" link are
driven by the frontmatter (`title`, `lede`, `pillar`, `section`) and rendered by
`src/layouts/BaseLayout.astro` — so you only ever edit prose, never navigation plumbing.

```
src/pages/
├── index.astro                     # home
├── open-government/
│   ├── index.md                    # the idea (summary)
│   ├── how-it-works.md
│   └── template.md                 # "clone your own" (roadmap sketch)
└── affordable-housing/
    ├── index.md                    # overview (summary)
    ├── the-model.md
    ├── governance-legal.md
    ├── pathway.md
    └── faq.md
```

## Deploy (GitHub Pages)

Pushing to `main` triggers `.github/workflows/deploy.yml`, which builds and deploys to GitHub Pages.

**One-time setup:** in the repo on GitHub, go to **Settings → Pages → Build and deployment → Source**
and choose **GitHub Actions**.

The site is configured in `astro.config.mjs` for a project site at
`https://krisrandall.github.io/age-of-abundance/`. If you add a custom domain later, set `base: '/'`
and update `site` accordingly.

## Roadmap

- Build the actual clonable **Open Government** template repository (currently sketched on the site).

---

*Content is general information, not financial or legal advice.*
