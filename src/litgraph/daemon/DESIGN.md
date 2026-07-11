# LiteratureGraph Daemon UI

Design language adapted from
[`external/awesome-design-md/design-md/resend/DESIGN.md`](../../../external/awesome-design-md/design-md/resend/DESIGN.md).

## Intent

Local admin hub (Home / Settings / Graph links). Dense, technical, print-magazine
confidence on a near-black canvas — not a purple SaaS dashboard.

## Tokens (implemented in `static/common.css`)

| Role | Value |
|---|---|
| Canvas | `#000000` |
| Surface | `#0a0a0c` / `#101012` |
| Ink | `#fcfdff` |
| Muted | `#a1a4a5` |
| Primary CTA | white on black |
| Link / focus | `#3b9eff` |
| Success | `#11ff99` |
| Danger | `#ff2047` |
| Display | Instrument Serif |
| UI | DM Sans |
| Mono | IBM Plex Mono |
| Radius | 8–12px (buttons/inputs/panels) |

## Brand mark

Icon assets (document + literature graph, coral accent):

| File | Use |
|---|---|
| `website/public/logo-icon.png` | Light surfaces / default favicon |
| `website/public/logo-icon-dark.png` | Dark UI (daemon, viz) |
| `docs/assets/brand/logo-icon-source-*.png` | Original art with gray canvas |

Daemon topbar uses `/ui/logo-icon-dark.png`.
