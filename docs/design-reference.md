# Design reference for agents

Spottr uses one visual system, "Red Lab". Reuse it. Do not introduce a second palette,
type scale, or set of primitives. When a screen needs a control that does not exist,
add it to `web/src/components/ui` additively and export it from
`web/src/components/ui/index.ts`.

Source of truth: `web/src/styles/theme.css` (tokens), `web/src/components/ui/`
(primitives), and `mockups/00-style-guide.html` + `mockups/01-home.html` (the visual
reference).

## Tokens

Use the Tailwind theme names; never hard-code hex values in components.

| Role                    | Token                           | Value                           |
| ----------------------- | ------------------------------- | ------------------------------- |
| App background          | `bg-lab-950`                    | `#0A0909`                       |
| Page / shell background | `bg-lab-900`                    | `#110E0E`                       |
| Soft surface            | `bg-lab-850`                    | `#161212`                       |
| Card surface            | `bg-lab-800`                    | `#1A1616`                       |
| Raised surface / inputs | `bg-lab-700`                    | `#251F1F`                       |
| Hairline / control ring | `lab-600`                       | `#2F2727`                       |
| Muted rule              | `lab-500`                       | `#3A3030`                       |
| Disabled / deep detail  | `lab-400`                       | `#4C4141`                       |
| Ash labels              | `ash-500`, `ash-400`, `ash-300` | `#6B6262`, `#8F8583`, `#A39996` |
| Body copy               | `text-bone-300`                 | `#C2B8B5`                       |
| Primary text            | `text-bone-100`                 | `#F0EBE8`                       |
| Accent / action         | `accent`                        | `#F0524A`                       |
| Accent hover            | `accent-soft`                   | `#F47A73`                       |
| Text on accent          | `accent-ink`                    | `#1A0605`                       |

Radii: `rounded-card` (20px) for cards, `rounded-panel` (24px) for large panels,
`rounded-full` for pills and controls. Circular data marks use full rounding.

## Type

- `display` — Archivo Expanded, uppercase, 800. Headlines, screen titles, primary
  buttons. Keep it short; use `leading-none` or `leading-[1.05]`.
- `eyebrow` — 9.5px expanded uppercase label, ash. Every section/card gets one.
- `num` — Martian Mono, tabular. Anything measurable: weights, reps, RPE, timers,
  dates, counts, tonnage.
- Body: Archivo, `text-sm`/`text-[15px]`, `text-bone-300`, relaxed leading.

Numbers are the visual anchor. Show the weight/reps large in mono and the label small
and muted, rather than the reverse.

## Layout

- Desktop shell is a 224px sidebar plus `max-w-[1180px]` content, `lg:px-10 lg:py-8`.
- Mobile is a single column with a floating bottom nav; leave `pb-32` clear space and
  place sticky action bars at `bottom-[calc(env(safe-area-inset-bottom)+88px)]`
  (see `web/src/features/coach/components/coach-screen.tsx`).
- Use a 1fr + 320px sidebar two-column layout for working screens; keep the sidebar
  sticky at `lg:top-8`.
- Cards: `bg-lab-800 rounded-panel p-[18px]`; inner controls on `bg-lab-700`.
- Hairlines are `ring-1 ring-inset ring-lab-600` or `border-lab-800`; avoid bright
  borders and drop shadows.
- Focus states come from the global `:focus-visible` accent outline. Do not remove it.
- Status color is accent, used sparingly. Never color large backgrounds with accent;
  primary buttons are the place for a solid accent fill.

## Existing primitives

`web/src/components/ui` exports `Button` / `buttonClasses`, `Card`, `Citation`,
`EmptyState`, `BrandMark`, `Logo`, `cn`, and the icon set (`BarbellIcon`,
`ChevronDownIcon`, `ChevronLeftIcon`, `ChevronRightIcon`, `CoachIcon`,
`HistoryIcon`, `PlusIcon`, `ProgressIcon`, `SendIcon`).

- Links that look like buttons use `buttonClasses`, not a second button component.
- `PageHeader` and `DemoNotice` live in `web/src/components/`, not `ui/`.
- Add missing icons or controls to the existing files rather than creating a
  parallel component library. Keep primitives feature-agnostic.

## Voice

Direct, physical, a little clipped. Use "working sets", "top set", "log", "session".
Labels are uppercase nouns ("LOAD KG", "REPS", "RPE"). Error copy says what happened
and what survives ("Couldn't save this workout. Your session is still here."). Avoid
exclamation marks, emoji, and decorative gradients.
