---
layout: ../../layouts/BaseLayout.astro
title: Clone your own
description: Open Government is meant to be a templated repository anyone can fork to publish their own declaration.
lede: Open Government is designed to be copied. Fork the template, fill it with your own values, publish.
pillar: open-government
section: template
---

<div class="callout warm">
  <span class="callout-title">Roadmap — not built yet</span>
  <p>This page sketches the clonable template. The actual repository is coming soon. The author will
  publish his own declaration first, and everyone is invited to copy it and make their own.</p>
</div>

## The idea

Open Government isn't a platform you sign up to — it's a **template you own**. The plan is a public
Git repository that anyone can **fork** (copy), fill in with their own values and priorities, and
publish. Your declaration lives in your own repo, under your own name. There's no central gatekeeper.

Because it's plain text in version control, every change is dated and visible. If your priorities
evolve, the history shows it honestly — which is itself a kind of accountability.

## Proposed repository structure

A first sketch of what the template would contain:

```
my-open-government/
├── README.md                  # who I am + how to read this declaration
├── the-world-i-want.md        # the overarching vision
├── the-government-i-want.md    # what government is for, given that world
├── my-priorities.md            # the concrete things government should secure
├── role-of-government.md       # the principle: who government serves first
├── positions/
│   ├── environment.md
│   ├── economy.md
│   ├── housing.md
│   └── ...                      # add your own
└── legislation-log/
    ├── EXAMPLE-bill-2026-001.md # one entry per bill: the bill, my read,
    └── ...                      #   and the AI-assisted comparison to my declaration
```

The **`legislation-log/`** is where the mechanism comes alive: each entry records a bill, your
position on it, and the comparison against your own declaration — the work that anyone could
reproduce with their own AI.

## How you'd use it

1. **Fork** the template into your own account.
2. **Fill in** the declaration files in your own words. Be plain and honest — this is the whole point.
3. **Publish** it (a repo, a simple site — whatever you like).
4. **Keep the log.** As legislation comes through, add entries comparing each bill to what you said
   you stand for.

When it ships, this page will link straight to the template so you can fork it in a click.
