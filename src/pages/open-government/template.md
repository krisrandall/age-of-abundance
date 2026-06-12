---
layout: ../../layouts/BaseLayout.astro
title: Clone your own
description: Open Government is meant to be a templated repository anyone can fork to publish their own declaration.
lede: Open Government is designed to be copied. Use the template, fill it with your own values, publish.
pillar: open-government
section: template
---

<div class="callout">
  <span class="callout-title">The template is live</span>
  <p>Copy it from GitHub:
  <a href="https://github.com/krisrandall/open-government"><strong>github.com/krisrandall/open-government</strong></a>.
  Click <strong>"Use this template"</strong> to make your own in one step. Everyone is invited to copy
  it and make it their own.</p>
</div>

## The idea

Open Government isn't a platform you sign up to — it's a **template you own**. The plan is a public
Git repository that anyone can **fork** (copy), fill in with their own values and priorities, and
publish. Your declaration lives in your own repo, under your own name. There's no central gatekeeper.

Because it's plain text in version control, every change is dated and visible. If your priorities
evolve, the history shows it honestly — which is itself a kind of accountability.

## What's in the template

```
open-government/
├── README.md                   # the idea + how to use it
├── the-world-i-want.md         # the overarching vision
├── the-government-i-want.md     # what government is for, given that world
├── my-priorities.md             # the concrete things government should secure
├── role-of-government.md        # the principle: who government serves first
├── positions/
│   ├── environment.md
│   ├── economy.md
│   └── housing.md               # duplicate to add your own areas
└── legislation-log/
    └── EXAMPLE-bill-2026-001.md # one entry per bill: the bill, your read,
                                 #   and the AI-assisted comparison to your declaration
```

The **`legislation-log/`** is where the mechanism comes alive: each entry records a bill, your
position on it, and the comparison against your own declaration — the work that anyone could
reproduce with their own AI.

## How you'd use it

1. **Copy it.** On [github.com/krisrandall/open-government](https://github.com/krisrandall/open-government),
   click **"Use this template"** (or fork it) to create your own copy.
2. **Fill in** the declaration files in your own words. Be plain and honest — this is the whole point.
3. **Publish** it (a repo, a simple site — whatever you like).
4. **Keep the log.** As legislation comes through, add entries comparing each bill to what you said
   you stand for.

→ **[Get the template on GitHub](https://github.com/krisrandall/open-government)**
