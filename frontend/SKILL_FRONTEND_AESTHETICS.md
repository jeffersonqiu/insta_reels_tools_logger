# Frontend aesthetics (Agent Skill snippet)

Use this when changing UI in this app. Source: [Improving frontend design through Skills](https://claude.com/blog/improving-frontend-design-through-skills) (Anthropic).

## Principles

- **Typography:** Prefer distinctive fonts (loaded from Google Fonts). Avoid default “AI slop” stacks: Inter, Roboto, Arial, generic system UI. This project uses **Outfit** + **JetBrains Mono** for hierarchy.
- **Color & theme:** One dominant mood + sharp accents. Use **CSS variables** in `src/index.css` and Tailwind extensions in `tailwind.config.js`—don’t scatter one-off hex values.
- **Motion:** Prefer a few high-impact moments (page/section entrance, staggered cards) over noisy micro-interactions everywhere. Prefer **CSS** animations; keep durations ~200–500ms with easing like `cubic-bezier(0.22, 1, 0.36, 1)`.
- **Backgrounds:** Layer gradients and subtle noise/texture instead of flat solid fills to add depth.

## Avoid

- Purple gradient on white “SaaS landing” clichés (we’re dark-first).
- Evenly timid palettes with no focal accent.
- Cookie-cutter card grids with no hover, border, or depth treatment.

## Compact prompt block (paste into agent context for UI work)

```text
<frontend_aesthetics>
Avoid generic "AI slop" UI. For this codebase: extend CSS variables + Tailwind theme; use Outfit/JetBrains Mono; layered dark backgrounds; accent lilac/teal sparingly; cards with border + blur + hover lift; staggered fade-up for lists.
Interpret creatively for the product (reel → tools feed), not a generic dashboard.
</frontend_aesthetics>
```
