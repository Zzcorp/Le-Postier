# Concept: Cimaise — Galerie contemporaine pour la Collection Samathey

# CIMAISE — Design spec « Galerie contemporaine »
### Identité visuelle & système UX pour Le Postier / Collection Samathey

*Cimaise (n.f.) : la tringle des galeries françaises sur laquelle on accroche les œuvres. Le système porte ce nom parce que c'est exactement son rôle : porter les cartes, puis disparaître.*

All contrast ratios below were computed (WCAG 2.1 relative luminance), not estimated. Constraints honored: Django server-rendered + vanilla JS, no build step, all fonts self-hosted woff2 from Google Fonts, French UI copy untouched.

---

## 1. Concept narrative

**The gallery, not the attic.** Today the site dresses antique postcards in antique clothing — brown gradients, floating fish, emoji dust, ochre everywhere. Cimaise inverts this: the *environment* becomes a contemporary French gallery — warm plaster walls, hairline rules, precise typography, silence — and the postcards become the only saturated objects on the page. Every CPA is treated as an accessioned artifact: matted on paper, numbered in small caps, captioned in a Garamond descended from Claude Garamont. The interface is near-monochrome (warm off-whites, warm near-black ink) with exactly one accent — *terre de Sienne*, refined from the existing brand ochre — spent like money: links, the one primary action per page, the wax-red moments of La Poste. When almost nothing has color, a 1904 hand-tinted postcard of Villefranche arrives like a spotlight.

**Warmth is structural, not decorative.** The risk of gallery minimalism is coldness; Cimaise avoids it the way good French galleries do — through material temperature rather than ornament. The whites are plaster and cream, never clinical #FFF. The black is heated with umber. The serif is French to the bone; the grotesque has humanist warmth. The surviving decorative vocabulary is drawn from French print and postal tradition — the *filet double* (double hairline rule) under headings, the *cachet de la poste* (circular datemark) as the intro's signature gesture, real handwriting for La Poste messages. Motion is calm and physical: things settle, flip, and stamp; nothing floats, sparkles, or fakes loading. The result should feel like the Musée de La Poste hired a very good Parisian studio — élégant, habité, and quietly proud of the collection.

---

## 2. Color tokens

Define once in `static/css/tokens.css` as CSS custom properties on `:root` (admin overrides on `.theme-noir`). This file replaces all ~30 hardcoded hexes and every `rgba(181,96,11,*)` variant found in the audit.

### 2.1 Light theme (public site)

**Backgrounds & surfaces — "les murs"**

| Token | Hex | Role |
|---|---|---|
| `--paper-0` | `#FBF9F4` | Page background. Warm plaster white — never `#FFF`. |
| `--paper-1` | `#F5F1E8` | Alternate sections, footer, hover fills, input backgrounds on paper-1 sections. |
| `--paper-2` | `#ECE6D9` | Insets, skeleton base, disabled fills, pressed states. |
| `--mat-0` | `#FFFFFF` | **Reserved exclusively for the postcard mat** (see §5.4). The only pure white on the site, so artifacts sit one step brighter than the wall. |

**Ink hierarchy — "l'encre"**

| Token | Hex | Role | Contrast on `--paper-0` |
|---|---|---|---|
| `--ink-900` | `#1F1B16` | Primary text, headings, primary buttons. Warm near-black (umber, not neutral). | **16.27:1** (AAA) |
| `--ink-700` | `#4A443B` | Secondary text, long body copy. | **9.15:1** (AAA) |
| `--ink-500` | `#6E675C` | Captions, metadata, placeholders. | **5.31:1** (AA); 4.96:1 on `--paper-1` — still AA. |
| `--ink-300` | `#A39A8B` | Disabled text/icons ONLY (2.64:1 — exempt under WCAG as disabled). Never for readable content. |

**Accent — "terre de Sienne" (the single accent)**

| Token | Hex | Role | Contrast |
|---|---|---|---|
| `--sienne-600` | `#B5600B` | Brand hue (kept from existing identity). Non-text uses: rules, active borders, focus rings, icons ≥24px, large display text ≥24px/700. | 4.30:1 on paper-0 — passes AA large-text & non-text (3:1), **not** body text. |
| `--sienne-700` | `#8F4A06` | **Text-safe accent**: links, accent buttons, active nav. | **6.34:1** on paper-0, 5.91:1 on paper-1 (AA). White text on it: 6.34:1. |
| `--sienne-800` | `#703A05` | Hover/active of accent elements. | **8.69:1** (AAA). |
| `--sienne-100` | `#F6E7D4` | Accent wash: selected chips, highlight rows, "rare" badge fill. ink-900 on it: 14.10:1; sienne-700 on it: 5.49:1. |

**Lines & borders — "les filets"**

| Token | Hex | Role |
|---|---|---|
| `--line-200` | `#E3DCCE` | Default hairlines: dividers, card edges, table rules. |
| `--line-300` | `#D1C8B6` | Input borders, postcard mat edge, hover-darkened hairlines. |
| `--line-ink` | `#1F1B16` | Emphasis borders (active tab underline, secondary button hover). |

**Feedback**

| Token | Hex | Role | Contrast on paper-0 |
|---|---|---|---|
| `--success-600` | `#2F6B4F` | Success text/icons (vert Empire, not Bootstrap green). | **5.98:1** (AA) |
| `--success-100` | `#E4EFE7` | Success toast/banner fill. |
| `--error-600` | `#9E2B25` | Errors (garance/madder red — a French pigment, not `#dc3545`). | **7.06:1** (AAA) |
| `--error-100` | `#F7E4E2` | Error fill. |
| `--focus-ring` | `#B5600B` | 2px `:focus-visible` outline + `outline-offset: 2px`, everywhere. 4.30:1 vs paper-0 — exceeds the 3:1 non-text requirement. |

Delete on sight: `#4ade80`, `#3b82f6`, `#28a745`, `#dc3545` and the Tailwind stat-icon rainbow.

### 2.2 Admin dark variant — "réserve" (the museum storeroom)

Scoped under `.theme-noir` on `<body>` of admin pages. Same token *names*, remapped — components are written against tokens and inherit the theme for free.

| Token | Hex | Role | Contrast |
|---|---|---|---|
| `--paper-0` → | `#14110D` | Page bg (warm bitumen, not blue-black). | — |
| `--paper-1` → | `#1C1812` | Cards, panels, table headers. | — |
| `--paper-2` → | `#262019` | Raised rows, inputs, hover fills. | — |
| `--ink-900` → | `#F2EDE3` | Primary text. | **15.14:1** on `#1C1812` (AAA) |
| `--ink-700` → | `#B8AE9E` | Secondary text, axis labels. | **8.06:1** on `#1C1812`, 7.36:1 on `#262019` (AAA) |
| `--ink-500` → | `#7E7566` | Muted meta, disabled (3.89:1 — non-text/disabled only; readable text uses ink-700). |
| `--line-200` → | `#332B21` | Hairlines. `--line-300` → `#453A2C`. |
| `--sienne-600` → | `#E39A3B` | Accent (chart primary, active nav, KPI deltas). | **7.53:1** on `#1C1812` — AA for text at any size. |
| `--sienne-700` → | `#EBAD5C` | Hover accent. | 8.97:1. |
| accent button | text `#14110D` on `#E39A3B` | | **8.02:1** |
| `--success-600` → | `#7FC49A` | | 8.64:1 |
| `--error-600` → | `#E5847C` | | 6.67:1 |

Charts (Chart.js — self-host the pinned file, per audit): series drawn from amber `#E39A3B`, then desaturated warm neutrals `#B8AE9E`, `#7E7566`, plus `#7FC49A`/`#E5847C` for good/bad only. No rainbow.

---

## 3. Typography

Two families public + one handwriting + one admin mono. All on Google Fonts; download woff2 (latin subset) via gstatic and serve from `static/fonts/` with `@font-face` + `font-display: swap`. Preload the two files used above the fold (`Cormorant Garamond 500`, `Instrument Sans variable`). **No `*` selector font rule** — set on `body` and let inheritance work (kills the 11 `font-family: inherit` workarounds).

### 3.1 Families

| Role | Family | Weights (woff2 files) | Why |
|---|---|---|---|
| Display / headings — « la voix de la collection » | **Cormorant Garamond** | 500, 600, 500-italic | A French Garamond revival — literally the national typographic heritage of the period the cards depict. High-contrast, museum-label elegance. Use ≥20px only. |
| UI / body — « la voix de la galerie » | **Instrument Sans** (variable) | 400, 500, 600 (+italic 400) | Crisp contemporary grotesque with humanist warmth; excellent at 14–18px; tabular-figures support via `font-variant-numeric`. |
| Handwriting — « la voix du correspondant » | **La Belle Aurore** | 400 | Uncannily close to real early-1900s French postcard handwriting. Replaces the never-loaded Dancing Script. Sizes ≥1.25rem only; `cursive` fallback. |
| Admin data | **Spline Sans Mono** | 400, 500 | IDs, IPs, counts, exports. Admin-only stylesheet. |

Stacks:
```css
--font-serif: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
--font-sans:  "Instrument Sans", "Helvetica Neue", Arial, sans-serif;
--font-hand:  "La Belle Aurore", cursive;
--font-mono:  "Spline Sans Mono", ui-monospace, monospace;
```

### 3.2 Scale (rem; base 16px; fluid via clamp, no build step needed)

| Token | Size | Family/weight | Line-height | Letter-spacing | Use |
|---|---|---|---|---|---|
| `--type-display` | `clamp(2.75rem, 6vw, 4.5rem)` | Serif 500 | 1.05 | −0.015em | Home hero « Collection Samathey » |
| `--type-h1` | `clamp(2.25rem, 4vw, 3rem)` | Serif 500 | 1.1 | −0.01em | Page titles |
| `--type-h2` | `clamp(1.625rem, 3vw, 2rem)` | Serif 600 | 1.2 | 0 | Section titles |
| `--type-h3` | `1.375rem` | Serif 600 | 1.3 | 0 | Card/modal titles |
| `--type-eyebrow` | `0.8125rem` | Sans 600, uppercase | 1.2 | **+0.14em** | Surtitre above headings (« LA COLLECTION »), rarity badges, nav labels |
| `--type-body-l` | `1.125rem` | Sans 400 | 1.65 | 0 | Presentation/long-form copy, max-width 65ch |
| `--type-body` | `1rem` | Sans 400 | 1.6 | 0 | Default |
| `--type-body-s` | `0.875rem` | Sans 400 | 1.5 | 0 | Metadata, form help |
| `--type-caption` | `0.8125rem` | Sans 500 | 1.45 | +0.01em | Postcard captions, timestamps |
| `--type-micro` | `0.75rem` | Sans 500 | 1.4 | +0.02em | Legal, footer sign-off |
| `--type-hand` | `1.375rem` | Hand 400 | 1.7 | 0 | La Poste messages, signatures |

**Rules.** Serif negative tracking only ≥36px; never track the serif positive. All-caps always sans, always +0.12–0.16em, never below 0.6875rem. Postcard numbers set as `Nº 0847` in eyebrow style, tabular figures (`font-variant-numeric: tabular-nums`). Dates in running serif text use oldstyle figures (`font-variant-numeric: oldstyle-nums` — Cormorant supports it). Italic serif reserved for artwork titles and French loan-phrases — exactly like a wall label.

---

## 4. Spacing, radius, shadow, border tokens

**Spacing** — 4px base, deliberately generous at the top end (whitespace is the luxury budget):
```css
--space-1: 0.25rem;  --space-2: 0.5rem;  --space-3: 0.75rem;  --space-4: 1rem;
--space-5: 1.5rem;   --space-6: 2rem;    --space-7: 3rem;     --space-8: 4rem;
--space-9: 6rem;     --space-10: 8rem;
```
Rhythm: section padding `--space-9` desktop / `--space-7` mobile; heading→content gap `--space-5`; grid gutters `--space-5` desktop / `--space-4` mobile. Page container `max-width: 1200px`, side padding `--space-5`/`--space-4`. Long-form measure 65ch. One shared header offset variable: `--header-h: 64px` (56px mobile) — kills the ad-hoc 60px compensations.

**Radius** — crisp, near-square (gallery frames aren't rounded):
```css
--radius-s: 2px;    /* buttons, inputs, chips */
--radius-m: 6px;    /* cards, panels, toasts, modals */
--radius-round: 999px; /* avatars, unread dots, count pills */
--radius-0: 0;      /* postcard images & mats — always sharp */
```

**Shadows** — museum lighting: soft, vertical, umber-tinted (never gray-blue):
```css
--shadow-1: 0 1px 2px rgba(31,27,22,.06);                          /* resting cards */
--shadow-2: 0 2px 6px rgba(31,27,22,.07), 0 10px 28px rgba(31,27,22,.09); /* hover lift */
--shadow-3: 0 8px 24px rgba(31,27,22,.14), 0 28px 72px rgba(31,27,22,.22); /* modals */
--shadow-inset: inset 0 1px 3px rgba(31,27,22,.08);               /* seats an artifact in its mat */
```

**Borders & rules:**
```css
--border-hair: 1px solid var(--line-200);
--border-input: 1px solid var(--line-300);
--filet-double: /* the signature French rule under h1/h2: */
  border-top: 1px solid var(--line-ink); + sibling 3px below: 1px solid var(--line-200); width 48px;
```
The *filet double* (short 48px double rule, ink over hairline) appears under page titles and in the footer — it is the system's monogram.

---

## 5. Component specs

All components live in extracted, cacheable files: `tokens.css`, `base.css`, `components.css`, per-page `pages/*.css` — no inline `<style>` blocks. Global focus style: `:focus-visible { outline: 2px solid var(--focus-ring); outline-offset: 2px; }`. Remove `user-select:none` and the contextmenu block entirely (a gallery lets you read the labels).

### 5.1 Buttons
Height 44px (48px on touch), padding-inline `--space-5`, radius `--radius-s`, sans 500 `0.9375rem`, letter-spacing +0.02em, transition 200ms.
- **Primary (ink):** bg `--ink-900`, text `--paper-0` (16.27:1). Hover: bg `#000` -adjacent `#14110D` + translateY(−1px) + `--shadow-1`. Active: translateY(0), `--paper-2` text unchanged. *This is the default primary — the gallery wears black.*
- **Accent (sienne):** bg `--sienne-700`, white text (6.34:1); hover `--sienne-800`. **Maximum one per view** — reserved for the money action: « Envoyer », « Créer mon compte », « Valider ».
- **Secondary:** transparent, `--border-input`, text `--ink-900`; hover: border-color `--line-ink`, bg `--paper-1`.
- **Ghost/link:** text `--sienne-700`, 1px underline, `text-underline-offset: 4px`; hover: `--sienne-800`, offset 6px (animated).
- **Destructive:** as Secondary but text/border `--error-600`; confirm-step turns solid.
- **Disabled:** bg `--paper-2`, text `--ink-300`, no shadow, `cursor: not-allowed`.

### 5.2 Inputs
Height 44px, radius `--radius-s`, bg `--mat-0` on paper-0 sections (`--paper-0` on paper-1), `--border-input`, text `--ink-900`, placeholder `--ink-500` (5.31:1 — readable, unlike most sites). Label above: `--type-body-s`, sans 500, `--ink-700`, margin-bottom `--space-2`. Focus: border `--sienne-600` + `box-shadow: 0 0 0 3px rgba(181,96,11,.18)` (plus the global focus-visible outline for keyboard). Error: border `--error-600`, message below in `--type-body-s` `--error-600` with `aria-describedby` + `aria-invalid="true"`. Textareas min-height 120px. Search fields get a left magnifier icon (16px, `--ink-500`) and a right « Effacer » ghost button when non-empty.
**6-digit code (verify_email):** six boxes 52×64px, `--radius-s`, digits sans 600 `1.75rem` tabular; filled box border `--line-ink`; first input `autocomplete="one-time-code"` + `inputmode="numeric"`; paste splits across boxes; auto-advance, Backspace retreats.

### 5.3 Cards (generic panels)
bg `--mat-0` (light) / `--paper-1` (admin), `--border-hair`, radius `--radius-m`, padding `--space-5`, `--shadow-1`. Hover (only when the whole card is a link): `--shadow-2` + border `--line-300`, 200ms. Card titles serif h3; meta row in `--type-caption` `--ink-500` separated by `·`.

### 5.4 Postcard frame treatment — the hero component
The artifact presentation, used identically in browse grid, modals, La Poste picker, profile favorites:
- **Mat:** the scan sits centered on `--mat-0` with a 12px mat (8px mobile) on all sides; outer edge `1px solid var(--line-300)`; radius 0 — sharp corners; `--shadow-inset` on the mat so the image reads as *placed*, not printed.
- **Scan:** `object-fit: contain` inside a fixed aspect box (3:2 landscape default; portrait cards letterbox on the mat — never crop an artifact). `image-rendering: auto`; lazy-loaded with `loading="lazy"` + `decoding="async"`.
- **Caption plate** below the mat, on the wall (not on the mat): line 1 — `Nº 0847` eyebrow style `--ink-500` + rarity badge right-aligned; line 2 — title in serif italic `1.0625rem` `--ink-900`, one line, ellipsis. Like a museum label: number, title, status.
- **Hover:** card lifts 2px, `--shadow-1`→`--shadow-2`, mat border darkens to `--line-ink` at 40%. **No image zoom on hover** — artifacts don't lunge at visitors.
- **Like:** a small heart button top-right *on the wall margin*, 32px hit area, `--ink-500` outline → filled `--sienne-600` when liked, with a 200ms scale 1→1.2→1 pop. `aria-pressed`, label « Ajouter aux favoris ».
- **Animated cards:** a small `▶` pastille (24px, ink-900 on mat-0 90%, hairline border) bottom-right of the mat.

### 5.5 Modal (postcard detail + all dialogs)
One shared implementation (`partials/modal.html` + `modal.js`) — replaces the two duplicated systems. Native `<dialog>` element (`showModal()` gives focus trap + Esc free), `aria-labelledby`, close on backdrop click *with* draft-guard for compose (see §7 La Poste). Backdrop: `rgba(20,17,13,.55)` + `backdrop-filter: blur(6px)`. Panel: `--mat-0`, radius `--radius-m`, `--shadow-3`, max-width 1040px, max-height 92vh.
**Postcard detail layout:** desktop — artifact zone left (65%, `--paper-1` wall with the matted card centered), label column right (65ch max: Nº + rarity, serif title, description body-s, keyword chips, view/zoom counts in caption gray, actions row: « Retourner la carte », « Zoom », like, « Envoyer cette carte » ghost link → La Poste with `?postcard=` prefilled — the audit's dead param, revived). Mobile — full-screen sheet, artifact on top, label below, sticky action bar. Zoom: click/pinch on the scan opens an edge-to-edge zoom layer with `transform`-based pan (no library), double-tap toggles 1×/2.5×, `Nº` watermark caption persists. Entrance: fade + scale 0.98→1, 240ms decel; exit 160ms. Flip: §6.4. Data comes from the gated detail/zoom APIs — fixes the rarity-bypass and dead view-count issues.

### 5.6 Navbar
**Desktop (≥900px):** fixed, `height: var(--header-h)` (64px), bg `rgba(251,249,244,.86)` + `backdrop-filter: blur(12px)`, bottom `--border-hair`. Left: Samathey logo (28px height, `alt="Collection Samathey — accueil"`). Center: text links in eyebrow style (0.8125rem caps +0.14em, `--ink-700`): Accueil · Parcourir · CP Animées · Présentation · Découvrir · Contact — **words, not icon-only**; current page `--ink-900` with a 1px `--sienne-600` underline sitting on the bar's bottom hairline (like a picture hung on the cimaise). Right: « La Poste » with unread pastille (`--radius-round`, `--sienne-600` bg, white tabular count, `aria-label="La Poste, 3 cartes non lues"`), avatar menu / « Connexion » ghost button. A skip link (« Aller au contenu ») is the first focusable element.
**Mobile (<900px):** 56px bar: logo left, La Poste envelope + pastille, burger (44px hit, `aria-expanded`). Panel: full-screen `--paper-0` overlay sliding from right 280ms decel; links in serif `1.75rem` stacked with `--space-5` gaps, staggered fade-up 40ms apart; footer of panel: auth actions + the filet double. Body scroll locked; Esc/backdrop closes; focus trapped. One breakpoint system site-wide: 600 / 900 / 1200px.

### 5.7 Footer
`--paper-1`, top `--border-hair`, padding `--space-8` / `--space-6` mobile. Three columns (stack on mobile): (1) Samathey logo + one serif italic line — « Cartes postales anciennes, France 1900 » ; (2) nav links body-s; (3) legal: Mentions légales, Confidentialité, gestion cookies (the CNIL-required consent revisit link lives here). Bottom line, centered, `--type-micro` `--ink-500`: filet double above « — A Z DATA Production 2025 — ».

### 5.8 Badges — rarity (museum tags, monochrome discipline)
Eyebrow type at `0.6875rem`, +0.12em, padding `2px 8px`, radius `--radius-s`, 1px border. The scale is *ink density*, not traffic-light colors:
- **Commune** — transparent bg, border `--line-300`, text `--ink-500`.
- **Rare** — bg `--sienne-100`, border `transparent`, text `--sienne-700` (5.49:1).
- **Très rare** — solid `--ink-900`, text `--paper-0` (16.27:1) — the black tag, the one collectors scan for.
Same component hosts stamp badges in La Poste (« 5c » vert Empire outline, « 10c » sienne outline) and admin statuses.

### 5.9 Toasts
Replace `#messages-container` styling. Fixed bottom-center (mobile) / bottom-right (desktop), stack max 3. Panel: `--ink-900` bg, `--paper-0` text, radius `--radius-m`, `--shadow-3`, padding `--space-3 --space-4`, left rule 2px in `--success-600`/`--error-600`/`--sienne-600` per type, close « × » button 32px. Container `role="status"` `aria-live="polite"` (`role="alert"` for errors). Entrance: fade + translateY(8px→0) 240ms decel; auto-dismiss 5s with a 1px depleting hairline; hover pauses. Reduced motion: instant show/hide.

### 5.10 Skeleton loaders
Real placeholders, replacing the fake 2.5s browse overlay (which is deleted). Skeleton = component silhouette in `--paper-2` with a slow sheen: `linear-gradient(100deg, transparent 30%, rgba(251,249,244,.7) 50%, transparent 70%)`, background-position sweep 1.6s ease-in-out infinite. Postcard skeleton: mat rectangle (aspect 3:2) + two caption bars (40%/70% widths). Disabled under `prefers-reduced-motion` (static `--paper-2`). Used for: browse page-loads, modal image fetch, La Poste tab switches, admin tables.

### 5.11 Pagination
Server-side (Django `Paginator`, 24/page — divisible by 2/3/4 grid columns), replacing the render-everything view. Centered under the grid: « Précédente » ghost / numbered squares 40×40 (`--radius-s`, sans 500 tabular; current = solid `--ink-900` white text + `aria-current="page"`; ellipsis for gaps) / « Suivante ». Mobile: Précédente · « Page 3 / 79 » (caption gray) · Suivante. Above the grid, left-aligned caption: « 1 894 cartes — page 3 sur 79 ». All links are real `<a href="?page=n">` preserving query params — crawlable, back-button-safe, no JS required.

---

## 6. Motion language

**Principle: « accrochage »** — the calm of hanging works in a gallery. Things settle into place; nothing bounces, floats or shimmers for its own sake. **All decorative animation systems are deleted**: particle injector, floating keywords, fish/seahorses/silures, light dots, emoji rain, dust. The motion budget saved is spent on five meaningful gestures.

**Durations & easings (tokens):**
```css
--dur-micro: 120ms;   /* hovers, toggles, likes */
--dur-std:   200ms;   /* buttons, borders, fades */
--dur-enter: 320ms;   /* content entrances, menus */
--dur-stage: 560ms;   /* flip, modal artifact, intro beats */
--ease-std:   cubic-bezier(0.2, 0, 0, 1);      /* default */
--ease-decel: cubic-bezier(0, 0, 0.2, 1);      /* entrances */
--ease-flip:  cubic-bezier(0.35, 0, 0.15, 1);  /* the flip */
```
Only `transform` and `opacity` are animated (compositor-only — no left/top mutation, ever again).

1. **Page arrival.** On DOMContentLoaded, `main` fades up (opacity 0→1, translateY 12px→0, `--dur-enter` decel); hero children stagger 40ms. Implemented as a class added by JS — **content is visible by default**; the audit's `[class*="animate-"]{opacity:0}` trap is abolished. Under `prefers-reduced-motion: reduce` (a single global media query zeroing all durations): no movement, instant opacity.
2. **Hover.** Cards: 2px lift + shadow, `--dur-std`. Links: underline-offset 4→6px. Buttons: 1px lift. Nothing scales except the like-pop.
3. **The flip (recto/verso)** — the signature interaction. Container `perspective: 1600px`; inner wrapper `rotateY(0→180deg)` over `--dur-stage` `--ease-flip`, both faces `backface-visibility: hidden`, verso pre-rotated 180°. Mid-flight the shadow deepens (`--shadow-2`→`--shadow-3`→`--shadow-2`) and the card scales 1→1.03→1 — it *lifts off the mat, turns in your hand, and settles*. Trigger: « Retourner la carte » button and clicking the artifact; announce face change to `aria-live`. Reduced motion: 150ms crossfade.
4. **Modal.** Backdrop fades 200ms; panel opacity + scale 0.98→1, 240ms decel; exit 160ms accel. The artifact inside gets a 60ms-delayed fade so it *arrives after its frame* — the unboxing beat.
5. **Intro (daily) — « le cachet du jour ».** Replaces the fake 3s loader. On `--paper-0`: (a) 0–500ms Samathey mark fades up; (b) 400–1400ms a circular *cachet de la poste* — SVG ring with « COLLECTION SAMATHEY » around the rim and today's date (French format) across the middle — stamps on at rotate(−8°), scale 1.15→1, 380ms with a single 2px settle, in `--sienne-600` at 85% opacity over the wordmark corner, exactly like a postmark over a stamp; (c) 1800ms wall fades to home. Total ≤2.2s, **any click/keypress skips instantly**, « Passer l'introduction » button visible from 0ms, honors reduced-motion (static composition, 800ms), once per day via localStorage, `?next=` validated server-side with `url_has_allowed_host_and_scheme`.

---

## 7. Per-page layout direction

**Accueil (home).** A gallery's opening wall: `--paper-0`, eyebrow « COLLECTION PRIVÉE — FRANCE 1900 », display-serif « Collection Samathey », one serif-italic line, primary ink button « Parcourir la collection ». Below the fold, one full-bleed `--paper-1` band with 3–5 matted highlight cards in an asymmetric row (one deliberately larger — curation, not grid), then a short serif-italic quote band about the collection, then three quiet entry cards (Parcourir / CP Animées / La Poste). Hero videos become one `<video muted loop playsinline>` behind a paper scrim at 88% — or a still scan; the per-request filesystem probing goes away with stored URLs.

**Intro.** As §6.5. It borrows nothing from base.html except tokens + fonts; dark theme is dropped — the cachet reads better on plaster.

**Parcourir (browse).** The main hall. Sticky sub-toolbar under the navbar (paper-0, bottom hairline): search field (60ch max), « Trier / Filtrer » secondary button opening a right-hand slide-over panel (real server-side sort/rarity/animated params — the placebo panel becomes functional), active-filter chips in `--sienne-100` with « × ». Grid: `repeat(auto-fill, minmax(280px, 1fr))`, gap `--space-5` — 4 columns at 1200px, 2 at 600, 1 below 420. Wall of matted postcards (§5.4), server-paginated (§5.11), skeletons during navigation. No forced overlay, no fish. Keyword bubbles become a single quiet row of ghost chips above the grid.

**CP Animées (animated gallery).** Same hall, projection room mood: keep `--paper-0` but mats display poster frames with the `▶` pastille; clicking opens the shared modal where the video plays (preload="none", poster from vignette). A caption under each: Nº + title + duration. Uses the same grid/pagination; the second modal system is deleted.

**Présentation.** The catalogue essay: 65ch centered serif-flavored long-form (`--type-body-l`), h1 + filet double, generous `--space-9` rhythm, one full-width matted archival image between sections, the timeline as a left-hairline list with sienne date markers (oldstyle figures). Delete presentation.css (conflicting dead file) and rebuild as `pages/presentation.css`.

**Découvrir.** Petit cabinet des curiosités: 2-column wall of framed paintings (mat + caption plate always visible — titles never hover-only), each an accessible `<button>` opening the shared modal with the story; video items use youtube-nocookie behind a click-to-load poster (consent-safe). The rickroll placeholder is retired with honors.

**Contact.** A correspondence desk: two columns — left, a matted blank-verso postcard visual where the visitor's message previews in La Belle Aurore as they type (the site's charm moment); right, the form (name + email added per audit, message textarea, stamp choice 5c/10c as real radio cards — both enable submit; the 5c trap dies). Success = toast + inline confirmation card with close button, never a page-covering overlay.

**La Poste.** The site's salon, and the one page where the accent breathes: paper-0, header « La Poste » serif + unread pastille, tabs (Reçues / Envoyées / Le mur) as eyebrow labels with the sienne cimaise-underline. Received cards stack as matted minis with a `--sienne-600` unread dot; opening one plays the flip and renders the message in `--type-hand` over a faint ruled-lines background, the 5c/10c stamp png top-right with the cachet overlapping it. Compose = shared modal: recipient autocomplete (escaped text, `textContent` only, display names not slugs), stamp radio cards showing « 44 caractères » vs « 300 caractères » *before* choice (10c→5c switch warns instead of truncating), postcard picker as a searchable paginated mat-grid (server search replaces the random-100 subset), live handwriting preview. Esc/backdrop with a dirty-draft confirm; send updates counts in place — no `location.reload()`.

**Profil.** A collector's card: header band paper-1 with avatar (radius-round, hairline ring), username serif h2, category as a badge, stat plate (Cartes aimées · Envoyées · Reçues in tabular figures over eyebrow labels, hairline-separated). Tabs below: Favoris (mat-grid of liked cards), Activité, Connexions (cards with « Écrire » wired to `/la-poste/?to=` — actually consumed now), Signature (draw/upload panel). Missing templates get built on this one layout.

**Auth flow.** One centered column, max-width 420px, on `--paper-0` with the wordmark above — a gallery membership desk, identical dark-free styling across all four steps (register joins the family; the gray Bootstrap card dies). A 3-step *filet* progress indicator (Coordonnées → Vérification → Mot de passe) with sienne current-step dot. Code screen per §5.2; password screen's checklist mirrors the server rules exactly; login gains « Mot de passe oublié ? » ghost link. Buttons: one accent button per screen.

**Admin (réserve).** `.theme-noir` per §2.2 — dark, dense, and disciplined: left rail nav (icons + labels, amber active rule on the cimaise line), 4-up KPI plates (Spline Sans Mono numerals `1.75rem`, eyebrow labels, amber deltas), Chart.js self-hosted/pinned with the §2.2 series palette, tables with `--line-200` row hairlines, sticky header, mono IDs/IPs, hover `--paper-2`. All innerHTML interpolation replaced with `textContent`/element building (XSS fix). admin_dashboard.css loads in `<head>`; tokens make it themeable without one hardcoded hex.

---

## 8. What makes this feel expensive rather than generic

1. **One accent, spent like money.** Sienne appears perhaps five times per viewport. Restraint is the most legible luxury signal there is — and it makes the postcards the most colorful objects on every page, which is the entire thesis.
2. **Material whites.** `#FBF9F4` walls with `#FFFFFF` reserved for mats means artifacts are *physically brighter than the room* — a real gallery-lighting trick, felt rather than noticed.
3. **Typographic scholarship.** A French Garamond for a French collection; small-caps accession numbers; oldstyle figures in dates; italic reserved for titles of works. These are wall-label conventions — museums are the most trusted brand language on earth.
4. **The filet double and the cachet.** Two proprietary marks drawn from French print and postal tradition, used consistently. Generic sites have no recurring marks; identities do.
5. **Hairlines instead of shadows.** 1px rules doing the separation work reads as print confidence; heavy drop shadows read as template.
6. **Motion that behaves like mass.** Five gestures, compositor-only, one easing family; the flip has weight, the modal has an unboxing beat, and *nothing* idles. Calm is expensive; churn is cheap.
7. **The absence of tricks.** No fake loaders, no placebo filters, no blocked right-click, no invisible-until-animated content. Honesty of mechanism is the UX equivalent of honest materials — and after the audit above, it's also the largest single upgrade this site can make.

---

### Appendix — implementation notes (no build step)
- `static/fonts/` + `fonts.css` with `@font-face` (woff2, latin subset, `font-display: swap`); preload Cormorant 500 + Instrument variable in `base.html` head.
- CSS load order: `tokens.css` → `fonts.css` → `base.css` → `components.css` → `{% block extra_css %}` per-page file. Delete orphan css/js identified in the audit.
- Fix `{% block page_title %}` placement, add per-page `<title>` + meta description + OG blocks to `base.html`; move GA behind a consent banner styled as a §5.3 card (bottom-left, ink buttons — a CNIL requirement, not a design option).
- Shared partials: `partials/modal.html`, `partials/postcard_frame.html`, `partials/pagination.html`, `partials/badge.html` — one source of truth each.
