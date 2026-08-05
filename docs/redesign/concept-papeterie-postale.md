# Concept: Papeterie Postale

# Papeterie Postale — Design System for « Le Postier » (Collection Samathey)

A complete visual identity + UX specification. Django server-rendered templates, vanilla JS, no build step, all assets self-hosted. All contrast ratios below were **computed** (WCAG 2.1 relative-luminance formula), not estimated; the admin chart palette was validated with a colorblind-safety validator (results cited in §2.4).

---

## 1. Concept narrative

**La papeterie postale.** Le Postier is not a website that displays postcards; it is a fine French stationery house that happens to have opened its private archive. Every surface is paper — warm cream stock, never white, never grey — and everything placed on that paper behaves the way objects behave on a correspondent's desk: matted photographs, affixed stamps, hairline-ruled forms, a cachet pressed in ink. The palette is disciplined to three inks a stationer would actually own: a warm sepia writing ink for all text, a **bleu postal** (the dusty marine of early Semeuse stamps) for actions and wayfinding, and a **rouge timbre** (10c brick-vermilion) reserved for the rare moments that deserve a seal — likes, unread mail, errors. Ochre survives only as gilt, rationed to the « très rare » tier. The typography is the narrative made literal: a true Garamond — the letterform cut in Paris — for display and reading, an early-grotesque sans for the working parts of the interface, and one fountain-pen hand reserved for what members actually write to each other.

**Restraint is the luxury.** The current site decorates (fish, particles, emoji, fake loading bars); the new site *finishes*. Postal motifs — stamp perforation, the circular postmark, deckled paper, the ruled verso of a card — appear at most **once per view**, executed precisely, like a blind emboss on good letterhead. Depth comes from millimetres, not gradients: 1px hairlines, a 3px double rule around a mat, a one-pixel letterpress press-in on a button. Motion is the motion of paper — cards lift 2px, flip on a real axis, a cachet stamps down once — and every animation yields instantly to `prefers-reduced-motion` and to the user's time (no artificial delays anywhere; the skeleton loader replaces every fake loading screen). The admin dashboard is the same house after dark: **le bureau de nuit**, the night sorting office — same paper hues inverted to warm darkness, dense and professional, never a different brand.

---

## 2. Color tokens

Single source of truth: `static/css/tokens.css`, loaded first from `base.html`. All values are CSS custom properties on `:root`; the admin dashboard re-declares the semantic aliases under `body.theme-bureau`. **This replaces the ~30 ad-hoc hexes and all 240 occurrences of `#b5600b`.**

### 2.1 Paper (backgrounds) & ink (text) — public site

| Token | Hex | Role | Contrast notes (computed) |
|---|---|---|---|
| `--paper` | `#F7F2E9` | Page ground. Warm cream stock. | — |
| `--paper-raised` | `#FCF9F2` | Cards, modals, inputs — "laid paper" one sheet up. | — |
| `--paper-sunken` | `#EFE7D7` | Wells, table stripes, commune chip, skeleton base. | — |
| `--paper-deep` | `#E6DBC4` | Hover state of wells, pressed ghosts, skeleton shimmer peak. | — |
| `--ink` | `#2B2118` | Primary text, headings. | **14.1:1** on `--paper` (AAA), 15.0:1 on raised |
| `--ink-soft` | `#5A4A38` | Secondary text, nav idle, captions that must read. | **7.6:1** on `--paper` (AAA) |
| `--ink-muted` | `#6E5D48` | Tertiary/meta text, placeholders, timestamps. | **5.7:1** on `--paper` (AA, any size) |

### 2.2 The three inks (accents & semantics)

| Token | Hex | Role | Contrast notes (computed) |
|---|---|---|---|
| `--postal` | `#275878` | **Bleu postal.** Links, primary buttons, focus rings, active nav, selection. | Text on paper **6.8:1** (AA+); `--paper-raised` text on postal fill **7.25:1** (AAA) |
| `--postal-deep` | `#1D4460` | Hover/active of postal; rare-badge text. | 9.2:1 on paper; cream on fill 9.8:1 |
| `--postal-tint` | `rgba(39,88,120,.10)` | Selected rows, rare chip bg (composites to `#E7E9E6` on raised). | — |
| `--stamp` | `#9E3626` | **Rouge timbre.** Likes, unread badges, destructive buttons, the compose seal. | Text on paper **6.3:1** (AA+); cream on stamp fill **6.6:1** (AA+) |
| `--stamp-tint` | `rgba(158,54,38,.08)` | Like-active wash, unread row wash. | — |
| `--error` | `#8F2B1E` | Form errors, failure toasts (deeper, more ink-like than `--stamp`). | Text on paper **7.4:1** (AAA); cream on fill 7.9:1. Error tint bg `#F5EAE2` → error text on it **7.0:1** |
| `--success` | `#28624A` | Success toasts, valid states, « envoyée » confirmations. | Text on paper **6.4:1**; cream on fill 6.8:1. Success tint `#ECEEE5` → text on it **6.1:1** |
| `--gilt` | `#7A4F12` | Gilt ink for « très rare » text and small gold accents. | **6.4:1** on paper (AA any size) |
| `--gilt-bright` | `#A87B2F` | Gilt for icons, large display accents, très-rare chip border. | **3.4:1** on paper — **≥24px text or non-text elements only** (passes 1.4.11 / large-text AA) |

*The old `#b5600b` maps to `--gilt-bright` where decorative and to `--gilt` where it was text; most occurrences should become `--postal` (actions) or `--ink-soft` (text) — ochre is no longer the action color.*

### 2.3 Lines, focus, scrim

| Token | Value | Role |
|---|---|---|
| `--line-hairline` | `1px solid #DCCFB8` | Default rules, card edges, dividers (decorative, no contrast req.) |
| `--line-strong` | `1px solid #B7A480` | Emphasized frames, table header rules |
| `--line-input` | `1px solid #92805E` | Form control boundaries — **3.65:1** vs `--paper-raised` (passes WCAG 1.4.11 non-text 3:1) |
| `--focus-ring` | `0 0 0 2px var(--paper), 0 0 0 4px var(--postal)` | Universal `:focus-visible` treatment (double ring reads on any bg) |
| `--scrim` | `rgba(20,16,13,.72)` | Modal backdrop — warm, never pure black |

### 2.4 « Le bureau de nuit » — admin dark variant

Same materials after dark; declared on `body.theme-bureau` by remapping semantic aliases (`--bg`, `--surface`, `--text-1` …) so components restyle automatically.

| Token | Hex | Role | Contrast (computed vs `#1E1813` surface) |
|---|---|---|---|
| `--bureau-bg` | `#14100D` | Page ground | — |
| `--bureau-surface` | `#1E1813` | Cards, panels, chart surface | — |
| `--bureau-raised` | `#28211A` | Hovered rows, dropdowns, modals | text 13.3:1 on it |
| `--bureau-text` | `#F2EADB` | Primary text | **14.7:1** (AAA) |
| `--bureau-text-soft` | `#C7BAA3` | Secondary | **9.2:1** (AAA) |
| `--bureau-text-muted` | `#9F9179` | Meta, axis labels | **5.7:1** (AA any size) |
| `--bureau-line` | `#3A3127` | Hairlines | decorative |
| `--bureau-line-strong` | `#4C4133` | Table rules, input borders | — |
| `--bureau-postal` | `#8FB6D9` | Links, active nav | **8.3:1** (AAA) |
| `--bureau-postal-btn` | `#2B6690` | Primary button fill | `--bureau-text` on it **5.2:1** (AA) |
| `--bureau-stamp` | `#E08A74` | Alerts, deletes, unread | **6.7:1** (AA+) |
| `--bureau-success` | `#8FBF9A` | Positive deltas | **8.4:1** (AAA) |
| `--bureau-gilt` | `#D6AC5E` | Très-rare, highlights | **8.3:1** (AAA) |

**Admin chart palette (Chart.js, self-hosted & version-pinned — replaces the unpinned CDN).** Categorical series colors, **assigned in this fixed order, never cycled, never repainted when a filter removes a series**:

| Slot | Hex | Hue |
|---|---|---|
| 1 | `#3987E5` | blue |
| 2 | `#D95926` | orange |
| 3 | `#199E70` | aqua-green |
| 4 | `#C98500` | gold |
| 5 | `#D55181` | magenta |

Validated against surface `#1E1813` with a six-check palette validator: all 5 slots pass lightness band (OKLCH L 0.48–0.67), chroma floor, adjacent-pair CVD separation (worst ΔE 8.4), normal-vision floor (worst ΔE 19.3), and ≥3:1 contrast vs surface. **First three slots additionally pass all-pairs** — for scatter/geographic dot maps cap at 3 series, fold the rest into « Autres ». Sequential ramps (heatmaps, hourly intensity) use blue only, light→dark. Status colors on stat tiles use `--bureau-success`/`--bureau-stamp` with an icon + label, never color alone. Chart text (values, axes, legends) always wears `--bureau-text-*` tokens, never a series color. Lines 2px; bars thin with 4px rounded ends and 2px gaps; every chart gets a hover tooltip; ≥2 series always get a legend.

---

## 3. Typography

### 3.1 The pairing (all on Google Fonts, self-hosted woff2, `font-display: swap`)

| Role | Family | Weights (files) | Why |
|---|---|---|---|
| Display + long-form reading | **EB Garamond** | 400, 500, 600 + 400 italic (latin + latin-ext) | A faithful revival of Claude Garamont's Parisian type — the letterform is literally French heritage; superb at display sizes, warm at text sizes. |
| UI / labels / data | **Work Sans** | 400, 500, 600 (latin + latin-ext) | Drawn from early-1900s grotesques — the sans of the postcard era. Crisp at 12–16px, excellent letterspaced caps, has `tabular-nums`. |
| Handwriting (postcard messages, signatures) | **La Belle Aurore** | 400 (latin) | Fountain-pen slant, genuinely reads as period correspondence — replaces the never-loaded Dancing Script. Used ≥ 1.25rem only. |

Self-hosting: download woff2 via google-webfonts-helper into `static/fonts/`; declare `@font-face` at the top of `tokens.css` with `unicode-range` for latin (`U+0000-00FF, U+2013-2014, U+2018-201D, U+20AC`) and latin-ext (covers `Œ/œ`). Preload the two above-the-fold files (`eb-garamond-600.woff2`, `work-sans-400.woff2`) in `base.html`. Fallback stacks: `Georgia, 'Times New Roman', serif` / `system-ui, 'Segoe UI', Arial, sans-serif` / `'Segoe Script', cursive`. **Never apply a family via the `*` selector** (kills the current 11 `font-family: inherit` workarounds): set serif on `body`, sans on a `.ui` utility + form elements, and let inheritance work.

### 3.2 Scale (rem, base 16px)

| Token | Size | Family/weight | Line-height | Letter-spacing | Use |
|---|---|---|---|---|---|
| `--type-display` | `clamp(2.5rem, 5.5vw, 4.25rem)` | Garamond 500 | 1.05 | −0.015em | Hero, intro title |
| `--type-h1` | 3rem | Garamond 500 | 1.1 | −0.015em | Page titles |
| `--type-h2` | 2.25rem | Garamond 500 | 1.15 | −0.01em | Section heads |
| `--type-h3` | 1.75rem | Garamond 600 | 1.25 | 0 | Sub-sections, modal title |
| `--type-h4` | 1.375rem | Garamond 600 | 1.35 | 0 | Card titles |
| `--type-lead` | 1.125rem | Garamond 400 | 1.7 | 0 | Editorial body (presentation, découvrir) |
| `--type-body` | 1rem | Garamond 400 | 1.65 | 0 | Default body |
| `--type-ui` | 0.9375rem | Work Sans 500 | 1.5 | +0.01em | Buttons, nav, form values |
| `--type-small` | 0.875rem | Work Sans 400 | 1.55 | +0.01em | Helper text, meta |
| `--type-label` | 0.75rem | Work Sans 600, **uppercase** | 1.4 | **+0.08em** | Field labels, badges, nav overlines, table headers |
| `--type-micro` | 0.6875rem | Work Sans 500 | 1.4 | +0.02em | Admin table meta only |
| `--type-hand` | 1.375rem | La Belle Aurore 400 | 1.9 | 0 | Postcard message body |
| `--type-hand-sign` | 1.75rem | La Belle Aurore 400 | 1.4 | 0 | Signatures |

**Rules.** Uppercase always carries ≥ +0.06em tracking; Garamond is never tracked positive. Editorial numbering uses Garamond 500 with old-style figures (`font-feature-settings: "onum"`) — « N° 0147 » is a recurring jewel. Data/tables use Work Sans with `font-variant-numeric: tabular-nums`. Reading measure: 68ch max on editorial pages. True small-caps where supported: `font-feature-settings: "smcp"` on `.label-sc` (Garamond has real small caps).

---

## 4. Spacing, radius, shadow, border tokens

### 4.1 Space (4pt grid)

`--space-1: 0.25rem` · `-2: 0.5rem` · `-3: 0.75rem` · `-4: 1rem` · `-5: 1.5rem` · `-6: 2rem` · `-7: 3rem` · `-8: 4rem` · `-9: 6rem`. Section rhythm: `--space-9` between page sections desktop, `--space-8` mobile. Card interior padding `--space-5`; dense admin interiors `--space-3/-4`. Content max-width `72rem` (1152px); editorial column `44rem`. **One breakpoint system everywhere: 640 / 900 / 1200px** (replaces the divergent navbar/page systems).

### 4.2 Radius — square, like paper

`--radius-1: 2px` (buttons, inputs, chips) · `--radius-2: 4px` (cards, vignettes, postcard corners) · `--radius-3: 8px` (modals, large panels) · `--radius-round: 999px` (pills, avatars, postmark). Nothing else. The near-square corner is a deliberate signature — pill buttons read as SaaS, 2px reads as print.

### 4.3 Shadow — warm ink, never black (light theme)

```css
--shadow-1: 0 1px 2px rgba(43,33,24,.07), 0 1px 1px rgba(43,33,24,.05);   /* resting card */
--shadow-2: 0 2px 6px rgba(43,33,24,.08), 0 10px 24px rgba(43,33,24,.09); /* lifted/hover */
--shadow-3: 0 4px 12px rgba(43,33,24,.12), 0 24px 48px rgba(43,33,24,.18);/* modal */
--shadow-press: inset 0 1px 2px rgba(43,33,24,.15);                        /* letterpress press-in */
--edge-emboss: inset 0 1px 0 rgba(255,255,255,.55), inset 0 -1px 0 rgba(43,33,24,.06); /* sunken wells */
```
Bureau de nuit: same three levels on `rgba(0,0,0,.35/.45/.55)`.

### 4.4 Frames

`.frame-hairline` = `border: var(--line-hairline)`. `.frame-double` (mats, modal, hero panels) = `border: var(--line-strong); outline: 1px solid #DCCFB8; outline-offset: 3px;` — the classic stationery double rule for the price of two declarations.

### 4.5 Postal motifs — the rationed signature set (max ONE per view)

- **Dentelure (stamp perforation).** An edge of punched half-circles: `background-image: radial-gradient(circle at 5px 0, transparent 3px, currentColor 3px)` tiled `10px` on an 8px strip (or an SVG mask for chip edges). Sanctioned uses: footer top edge, très-rare chip, auth ticket strip, the stamp slots in La Poste/Contact.
- **Le cachet (postmark).** One inline SVG: two concentric circles, « COLLECTION SAMATHEY » on the upper arc, date across the middle, « LA POSTE — 5ᶜ » lower arc. Uses: intro reveal, like-action stamp, 4%-opacity watermark behind page headers, profile seal.
- **Verso ruling.** `repeating-linear-gradient(transparent 0 1.85em, #DCCFB8 1.85em calc(1.85em + 1px))` as the background of message textareas — the ruled correspondence side of a card.
- **Deckled edge.** SVG-mask data-URI, reserved for the home hero paper panel only.

---

## 5. Component specifications

### 5.1 Buttons (Work Sans 600, `--type-ui`, radius `--radius-1`, min target 44×44px)

- **Primary « cachet »** — fill `--postal`, text `--paper-raised`, padding `0.75rem 1.5rem`, letter-spacing +0.02em. Hover: `--postal-deep` + `--shadow-1` (200ms). Active: `translateY(1px)` + `--shadow-press`. Focus: `--focus-ring`. Disabled: `--paper-sunken` bg, `--ink-muted` text, no shadow, `cursor: not-allowed`.
- **Secondary** — transparent, `1.5px solid --postal`, text `--postal`; hover fills `--postal-tint`.
- **Ghost** — text `--postal`, underline `text-underline-offset: 3px` appearing on hover; used inline.
- **Destructive** — fill `--stamp` (hover `--error`), cream text.
- Sizes: sm `0.5rem 1rem / 0.875rem`; lg `0.9375rem 2rem / 1rem`. Icon buttons: 44px square, hairline border, radius-1.

### 5.2 Inputs

Field = label + control + helper. Label: `--type-label`, `--ink-soft`. Control: bg `--paper-raised`, `--line-input` border, radius-1, padding `0.75rem 1rem`, text `--ink` in Work Sans 400 1rem; placeholder `--ink-muted` **EB Garamond italic** (« Votre message… » — a small charm). Focus: border-color `--postal` + `box-shadow: 0 0 0 3px rgba(39,88,120,.18)`. Error: border `--error`, helper text `--error` with ⚠ icon, `aria-describedby` wired, never color-alone. Textareas for correspondence get the **verso ruling** background with `line-height: 1.85em` locked to the rules. Select/checkbox/radio: same border ink; checked = `--postal` fill, cream check. **6-digit code**: six 52×64px wells, `--edge-emboss` inset, Garamond 600 1.75rem centered digits, gap `--space-2`, single hidden input with `autocomplete="one-time-code" inputmode="numeric"` (fixes broken mobile OTP autofill), auto-advance + paste-splitting.

### 5.3 Cards (generic)

`--paper-raised` bg, hairline frame, radius-2, `--shadow-1`, padding `--space-5`. Hover (interactive cards only): `translateY(-2px)` + `--shadow-2`, 200ms ease-out. Title `--type-h4`, meta `--type-small --ink-muted`. Whole card clickable → wrap in `<a>` with inner elements non-focusable; visible focus ring on the card.

### 5.4 Postcard frame — the signature component

A vignette is **matted, never naked**: outer card (raised paper, hairline, radius-2) → inner mat padding `--space-3` (`--space-4` featured) → image with 1px hairline and radius `3px` (real postcards have rounded cuts), `object-fit: cover` at `aspect-ratio: 7/5` in the grid (CPA standard 14×9). Below the mat: « N° 0147 » in Garamond onum `--ink-muted` left, rarity chip right; title `--type-h4` one line ellipsed. Rarity chip overlays top-left of the image only for très-rare. Featured/hero postcards upgrade to `.frame-double` mats plus optional CSS-only photo-corner triangles (`--paper-sunken`, 14px, one per corner) — home page only. Like button: bottom-right of mat, 36px, outline heart in `--ink-muted` → filled `--stamp` when liked (see §6 for the cachet animation). Images `loading="lazy"` + `width/height` attributes; hover: image `scale(1.02)` inside the mat (300ms), card lifts.

### 5.5 Modal — postcard detail (one component, one partial: rebuild `partials/postcard_modal.html`, delete both inline duplicates)

Backdrop `--scrim` + `backdrop-filter: blur(3px)`. Dialog: `--paper-raised`, radius-3, `.frame-double`, `--shadow-3`, max-width 1040px, max-height 92vh. Header: « N° » + title (Garamond h3) left; close (44px icon btn) right. Body: the card at max size on a deep mat, **recto/verso flip control** (« Voir le verso » ghost button + clicking the card flips — §6.4), zoom button (opens the zoom layer: image at natural size in a pannable overflow container, pinch/scroll zoom, Esc closes layer first), like with count. Footer: prev/next arrows (« Précédente / Suivante », keyboard ← →). Accessibility: `role="dialog" aria-modal="true"`, `aria-labelledby` the title, focus trapped, focus returns to the opening card, Esc closes, body scroll locked. Mobile ≤640px: full-screen sheet sliding up 280ms, close as a top-left chevron, flip/zoom/like as a 56px bottom action bar. Rare-tier gating happens server-side (the modal fetches the gated detail endpoint; high-res/verso URLs are **not** pre-embedded in the grid DOM — fixes the bypass).

### 5.6 Navbar

**Desktop (>900px):** fixed 64px bar, `rgba(247,242,233,.88)` + `backdrop-filter: blur(8px) saturate(1.1)`; bottom hairline + `--shadow-1` appear only after 8px scroll. Left: Samathey logo (28px tall, `alt="Collection Samathey — accueil"`). Center: text links (Accueil · Parcourir · CP Animées · Découvrir · Présentation · Contact) in `--type-ui` `--ink-soft`; hover `--ink`; **active page: `--ink` + 2px `--postal` underline sitting on the bar's bottom edge — a filing-tab.** Right: La Poste icon (envelope) with `--stamp` unread pill (`aria-label="La Poste, 3 non lues"`), profile avatar/« Connexion » ghost button. A skip-link (`.visually-hidden` until focused) precedes everything. The `page_title` block moves out of the navbar into `base.html`'s `<title>`+`<h1>` chain (fixes the dead-block bug; every page gets a unique title + meta description).
**Mobile (≤900px):** 56px bar: logo left, La Poste icon + burger (44px) right. Burger opens a full-screen `--paper` panel sliding from the right (280ms), links in Garamond 1.5rem stacked with 30ms stagger, connexion/profil pinned at bottom above a small postmark watermark. `aria-expanded` on the burger, focus trapped, Esc closes.

### 5.7 Footer

`--paper-sunken` band with the **dentelure top edge** (its one sanctioned appearance on most pages). Three columns (stack ≤640px): ① logo + « Collection privée de cartes postales anciennes » in Garamond italic; ② navigation links; ③ Contact · **Mentions légales · Confidentialité** (legally required in France — pages to create; the cookie-consent link for GA lives here too). Bottom rule then « — A Z DATA Production 2025 — » in `--type-label` centered. Links `--ink-soft` hover `--postal`.

### 5.8 Rarity badges

All chips: `--type-label` (12px caps, +0.06em), radius-1, padding `2px 8px`, 1px border.
- **Commune** — bg `--paper-sunken`, text `--ink-soft` (**6.9:1**, AA), hairline border.
- **Rare** — bg `--postal-tint` (composite `#E7E9E6`), text `--postal-deep` (**8.4:1**, AAA), border `rgba(39,88,120,.35)`.
- **Très rare** — bg `rgba(168,123,47,.14)` (composite `#F0E7D7`), text `--gilt` (**5.8:1**, AA), border `--gilt-bright`, and the chip's left/right edges are **perforated** (SVG mask) — the only chip that gets the jewellery. Optional ✦ prefix.
Never color-alone: the label text *is* the information.

### 5.9 Toasts

Replace bare Django message divs. Container top-right (top-center ≤640px), `aria-live="polite"` (`role="alert"` only for errors). Toast: `--paper-raised`, radius-2, `--shadow-2`, 3px left rule + icon in the semantic color, text `--type-small --ink`, close ×. Enter: fade + `translateY(-8px)` 240ms; auto-dismiss 5s (errors persist); reduced-motion: instant. Max 3 stacked.

### 5.10 Skeleton loaders (replacing every fake loading screen)

Blocks of `--paper-sunken`, radius matching the final element; shimmer = a `--paper-deep` gradient sweep, 1.4s ease-in-out infinite; static under reduced-motion. Postcard skeleton = mat + 7:5 image block + two text lines (40%/70%). Grid shows 12 instantly while fetching. **Delete `MIN_LOADING_TIME` and both forced overlays — perceived speed is the brand.** Real image loading: hairline-bordered cream placeholder → image fades in 300ms on `load`.

### 5.11 Pagination (browse becomes server-paginated, 36/page)

Centered row, Work Sans. « Précédente » / « Suivante » as ghost buttons with arrows; numbered squares 40×40px radius-1: idle `--ink-soft` hairline-bordered on hover; **current = `--postal` fill, cream numeral** (`aria-current="page"`); ellipsis `--ink-muted`. Mobile: prev/next + « Page 3 / 53 » in Garamond onum. Filters/search/sort round-trip as querystring params the view actually reads (fixes the placebo panel), each active filter shown as a dismissible chip above the grid.

---

## 6. Motion language

### 6.1 Tokens

```css
--dur-1: 120ms;  /* micro: color, underline      */
--dur-2: 200ms;  /* standard: hover, lift, press */
--dur-3: 280ms;  /* panels, drawers, toasts      */
--dur-4: 420ms;  /* modal, page fade             */
--dur-flip: 640ms;
--ease-out:   cubic-bezier(0.22, 0.61, 0.36, 1); /* default */
--ease-enter: cubic-bezier(0.16, 1, 0.3, 1);     /* entrances, slight settle */
--ease-flip:  cubic-bezier(0.45, 0, 0.2, 1);
```

**Global policy:** animate only `transform`, `opacity`, `box-shadow` (compositable). One `@media (prefers-reduced-motion: reduce)` block in tokens.css collapses durations to 1ms and disables shimmer/flip-3D (flip degrades to a 200ms crossfade). Content is **visible by default** — entrance keyframes animate *from* opacity 0, base state stays `opacity: 1` (kills the `[class*="animate-"]{opacity:0}` invisibility trap). Every ambient system dies: fish, seahorses, silures, particles, floating emoji, dust. Ambience is now the 4%-opacity postmark watermark — static.

### 6.2 Page transitions

Server-rendered; `<main>` fades in with an 8px rise (`--dur-4 --ease-enter`) via one keyframe on page load. On grids, the first 12 mats stagger 25ms each, one time, on first paint only. No exit animations, no artificial waits, ever.

### 6.3 Hover grammar

Cards lift 2px + shadow-2; images breathe to `scale(1.02)` inside their mat; links slide in a 1px underline (`background-size` trick, `--dur-1`); buttons darken then **press in** on `:active` (translateY 1px + `--shadow-press`) — the letterpress signature; nav tabs grow their underline from center (`--dur-2`).

### 6.4 The postcard flip

3D: container `perspective: 1200px`; inner wrapper `transform-style: preserve-3d; transition: transform var(--dur-flip) var(--ease-flip)`; recto/verso absolutely stacked with `backface-visibility: hidden`, verso pre-rotated `rotateY(180deg)`. Flip = wrapper to `rotateY(180deg)`. During flip a soft shadow sweep (pseudo-element opacity 0→.12→0) sells the paper turning. Announce state via `aria-pressed` on the flip button + visually-hidden « Verso affiché ». Reduced-motion: 200ms crossfade.

### 6.5 The like — « le coup de tampon »

On like, the cachet SVG stamps onto the mat corner: scale 1.4→0.96→1 with opacity 0→.85, 320ms `--ease-enter`, in `--stamp` ink; heart fills simultaneously; count ticks up with a 6px rise. Unlike simply fades it 200ms. This is the site's one moment of theatre — nothing else may imitate it.

### 6.6 Intro (daily) — « Le cachet du jour »

≤ 2.4s, on `--paper`: ① the postmark SVG self-draws (stroke-dashoffset, 900ms `--ease-out`), today's date inside; ② « Collection Samathey » fades up in Garamond display, tracked +0.04em easing to −0.01em (500ms, overlapping); ③ the whole screen lifts away (scale 1.02 + fade 420ms) into the home page. A « Passer l'introduction » ghost button is visible from 0ms; any click/key skips. Progress bars and fake status messages are deleted. Reduced-motion: static composition 800ms, then through. The `?next=` redirect is validated server-side (`url_has_allowed_host_and_scheme`).

---

## 7. Per-page layout direction

**Accueil (home).** A single deckle-edged cream hero panel: « Collection Samathey » in display Garamond over one large matted postcard — **« La carte du jour »** (deterministic date-seeded pick, replacing `order_by('?')` + video probing) — with its N°, rarity chip and a « Découvrir la collection » primary button. Below: three quiet entry cards (Parcourir · CP Animées · La Poste) as matted thumbnails with Garamond titles, then a one-paragraph collection introduction in `--type-lead` italic. No particles, no video wall; one image, perfectly framed.

**Intro.** As §6.6 — a standalone template that imports tokens.css (no duplicate palette), postmark reveal, always skippable, sessionStorage per day.

**Parcourir (browse).** A calm sticky toolbar under the navbar (`--paper-raised`, hairline bottom): search input with Garamond-italic placeholder, working sort/rarity/animated selects, active-filter chips. Grid of matted vignettes — 2 cols ≤640, 3 to 1200, 4 above — server-paginated at 36, skeletons while images land. Keyword bubbles become quiet `--postal-tint` chips above the grid. Modal per §5.5. All aquarium/particle systems removed; the header carries the static postmark watermark.

**CP Animées (animated gallery).** The one dark public room — « la salle de projection » : page stays cream but the video wall sits on an `--ink`-colored panel with `--paper` captions and gilt N°s, like projections in a darkened cabinet. Cards show poster frames with a small ▶ cachet; hover/focus plays muted preview; click opens the shared modal in video mode. Uses a stored `has_animation` flag (no per-request disk scans).

**Présentation.** Pure editorial: 44rem column, `--type-lead` Garamond with a drop cap on the opening paragraph, h2s with short hairline overlines, the collection's history as a vertical timeline — a 1px `--line-strong` rule with small postmark nodes and dates in `--type-label`. One full-bleed matted postcard as a mid-page rest.

**Découvrir.** A gallery wall on `--paper`: paintings/videos in deep double-rule mats on a generous grid, **captions always visible** beneath each frame (title in Garamond, medium in `--type-small`) — nothing hover-only; every frame a real `<button>` with focus ring. Modal shares §5.5 chrome with a self-hosted or `youtube-nocookie` embed behind consent. The rickroll placeholder is replaced or the frame removed.

**Contact.** The writing desk: the form *is* a postcard verso — a raised 7:5 card, divider rule down the middle ≥900px; left half the ruled message textarea (verso ruling background), right half To/From fields (**add sender email + name to the form**) and the address block; top-right, the 5c/10c stamp slot — choosing affixes the stamp with a 6° settle rotation, **both stamps valid** (the 5c-disables-submit trap is removed; if a length rule exists it is stated under the field with a live counter and `aria-live`). Success: the cachet stamps across the card + a success toast — dismissible, auto-clearing, never a permanent overlay.

**La Poste.** The heart of the social feature: a postmaster's desk. Header: title + unread pill. Two filing-tab trays (« Reçues » / « Envoyées ») — received cards stack as envelopes; opening one flips it full-size with the sender's message in La Belle Aurore and their signature; read-state updates every badge live (header pill, tab count, item) via one JS store. « Écrire une carte » opens a 3-step compose sheet: ① choose the card (searchable, server-paginated picker — no random subsets; honors `?postcard=` and `?to=` preselection); ② write — ruled textarea rendered live in `--type-hand`, recipient autocomplete showing display-name category labels (escaped, via `textContent`); ③ affix the stamp — 5c (44 char) / 10c (long) slots with dentelure edges, a live counter, and an explicit warning before any truncation when switching 10c→5c; send = the cachet strikes the stamp, then the card slides off-screen right (420ms) — no full-page reload. « Le mur » (public wall) below as a matted pinboard, comment counts denormalized. Floating emoji and dust particles deleted.

**Profil.** « La carte de membre » : header as a library-card panel — avatar in an oval hairline frame, username in Garamond h2, member-since in `--type-label`, the user's signature rendered in `--type-hand-sign`, a personal cachet at the right edge. Below: four stat tiles (cards sent/received, likes, favorites — served by a real, routed stats endpoint), then filing-tab sections (Activité · Connexions · Favoris · Réglages) as in-page tabs on one working template (replacing the five 500-ing routes). Connection cards carry « Écrire » wired to `/la-poste/?to=…`.

**Auth (connexion / inscription / code / mot de passe).** One unified funnel on `--paper`: a centered 26rem raised card with `.frame-double`, the Samathey logo small on top, and — for the 3 registration steps — a **perforated ticket-strip progress indicator** (three stubs, done = `--postal` fill, current = outlined, labels in `--type-label`). Register drops the grey Bootstrap look for the house style; code entry uses §5.2 wells with resend link + expiry note; set-password shows a checklist that mirrors the *server's* actual rules, with the match-indicator rebuilt (text and class always set together). Login gains « Mot de passe oublié ? » (flow to be added). Email-send failures surface a visible French error. `?next=` validated.

**Admin (bureau de nuit).** `body.theme-bureau`, Work Sans throughout, tabular numerals, dense `--space-3` rhythm. Fixed 240px left rail (`--bureau-bg`, gilt-accented active items), topbar with period filters in one row. Content: stat tiles (value 2rem/600, delta with ▲▼ icon + color, label `--type-label --bureau-text-muted`) then chart cards on `--bureau-surface` with hairline borders — palette and mark rules per §2.4; Chart.js vendored and pinned; CSS moved to `<head>` (kills the FOUC); all `innerHTML` interpolations replaced with `textContent`/element building (kills the stored-XSS vector). Tables: 13px, `--bureau-line` row rules, sticky header, row hover `--bureau-raised`. It reads as the same stationery house — cream inks on warm darkness, gilt for emphasis — never a generic admin theme.

---

## 8. What makes this feel expensive rather than generic

1. **Paper, not white.** The whole site sits on `#F7F2E9` stock with sepia ink — instantly non-template, and it flatters sepia postcards the way museum matting flatters photographs.
2. **Three inks, total discipline.** One blue, one red, one gilt — each with a fixed meaning (action / seal / rarity). Generic sites leak accent colors; this one rations them like a stationer rations engraving.
3. **A true Garamond used with editorial manners** — old-style figures in « N° 0147 », real small caps, tracked-caps labels, a 68ch measure. Typographic detail at this level is the single strongest luxury signal on the web.
4. **Millimetre depth instead of decoration.** Hairlines, double-rule mats, a 1px letterpress press-in on every button — depth you *feel* rather than gradients you see.
5. **One motif per view.** Perforation, postmark, deckle and ruling exist, but never together — the restraint is what separates papeterie from scrapbook.
6. **One moment of theatre** — the cachet stamping on a like — and everything else calm. A single owned interaction is a brand; twelve animations are noise.
7. **Speed as courtesy.** No fake loaders, no forced 2.5s waits, server pagination, cached image URLs, skeletons that resolve in real time. On a heavy-mobile audience, instant *is* premium.
8. **Everything is finished** — focus rings designed rather than default, empty states written in French with the house voice, error text in real error ink at 7:1, the admin wearing the same identity after dark. Expensive is the absence of loose threads.

---

## Appendix — implementation notes (no build step)

- **Files:** `static/css/tokens.css` (custom props + @font-face + reduced-motion block) → `static/css/base.css` (reset, layout primitives, type classes) → `static/css/components.css` (§5) → one small `static/css/page-*.css` per page, all linked in `<head>` via `{% block extra_css %}`. All 16 inline `<style>` blocks migrate out; dead files (`browse.css`, `contact.css`, `home.css`, `presentation.css`, `gallery.css`, `browse.js`, `gallery.js`, empty modal partial, `admin_sync_ovh.html`) are deleted.
- **JS:** `static/js/ui.js` (nav, toasts, modal + focus trap, flip, like) in vanilla ES2017; per-page files for browse/la-poste/profile. `main.js`'s particle and ghost-ID code is deleted.
- **Base template:** unique `<title>` + meta description per page, OG tags, canonical, correct favicon MIME; GA loads only after consent (a small cream banner, CNIL-compliant); `user-select` and `contextmenu` blocks removed.
- **Accessibility floor:** skip link, `:focus-visible` everywhere, `role="dialog"`+trap on all modals, `aria-live` toasts, alt text pattern « Carte postale N° 147 — [title], recto », WCAG AA verified per the computed tables above, unified breakpoints, 44px touch targets.
