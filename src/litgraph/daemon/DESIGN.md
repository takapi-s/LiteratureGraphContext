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

## Rules

- Scarce chromatic accents: blue for focus/links, green for healthy status, red for destructive only.
- No purple brand fill, no multi-layer card shadows, no pill CTAs.
- Hairline borders (`rgba(255,255,255,0.06–0.14)`) carry elevation instead of drop shadows.
- Brand wordmark is hero-level on Home; nav stays secondary.
