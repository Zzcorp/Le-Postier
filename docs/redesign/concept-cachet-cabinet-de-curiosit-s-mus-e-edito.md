# Concept: Cachet — Cabinet de curiosités / musée (editorial heritage)

# CACHET — Système de design « Le Postier / Collection Samathey »

Angle: cabinet de curiosités / catalogue d'exposition. Version 1.0. All values are final and implementable as-is in `static/css/base.css` custom properties + self-hosted woff2. No build step, no CDN.

---

## 1. Concept narrative

**Le site n'est pas un site sur des cartes postales ; c'est le catalogue d'une exposition permanente.** Every screen borrows its logic from the museum: postcards are hung on a warm plaster wall (vélin paper background), matted in a white *passe-partout*, labeled with a *cartel* (the small engraved label beside an exhibit: number, title, date, in letter-spaced small caps). The palette is extracted from the artifacts themselves — the cream of a 1905 card back, sepia ink, the ochre already in the brand (#B5600B), and the two Semeuse stamps: the 5c green and 10c red become the site's success and error colors, so even system feedback speaks the collection's language. Typography is French to the bone: a Garamond lineage (Cormorant for display, EB Garamond for text — Claude Garamont's own punches), real small caps echoing the « CARTE POSTALE » letterpress header on every verso, and a single handwriting face reserved for what is actually handwritten: messages sent through La Poste, echoing the ink signature of the Samathey logo.

**Restraint is the luxury.** The current site's fish, particles, forced loaders and emoji dust are replaced by one motion idea: objects presented to you — cards rise gently into place, the modal opens like a vitrine, the recto/verso flip is the one theatrical gesture and it is physically convincing. Ornament is engraved, not applied: hairline rules, a double *filet* border on frames and section heads, oldstyle numerals, a circular postmark (*cachet à date*) as the recurring graphic device (intro, footer, empty states, loading). Dark is used the way museums use it — for the cabinet moments: the daily intro, the overlay menu, the footer, and the admin back-office, all sharing one "cabinet" palette so the system never splits in two. Nothing bounces, nothing glows, nothing is faked; the site feels expensive because everything on screen looks placed by a curator's hand.

---

## 2. Color tokens

All contrast ratios computed against WCAG 2.1. "AA text" = ≥4.5:1 normal text; "AA large/UI" = ≥3:1.

### 2.1 Light theme — « la salle » (all public pages)

| Token | Hex | Role | Contrast notes |
|---|---|---|---|
| `--bg-page` | `#F5EFE2` | Page background, warm vélin | base ground |
| `--bg-surface` | `#FCFAF3` | Cards, modals, inputs, navbar | base ground |
| `--bg-well` | `#EDE5D2` | Recessed zones: alternate sections, skeleton base, verso ground | base ground |
| `--bg-mat` | `#FFFEF9` | Passe-partout mat around postcard images | decorative |
| `--ink-1` | `#2B2118` | Primary text, headings (sepia near-black) | 13.7:1 on page — AAA |
| `--ink-2` | `#5B4A38` | Secondary text, cartel labels (bistre) | 7.4:1 on page — AAA |
| `--ink-3` | `#7A6A55` | Captions, meta, placeholders | 4.6:1 on page/surface — AA. On `--bg-well` it drops to 4.2:1: use `--ink-2` there, or ≥1.25rem |
| `--ink-faint` | `#A29377` | Decorative only (rules, watermarks) — never for text | fails AA, by design |
| `--accent` | `#B5600B` | Brand ochre: icons, large display accents, active underlines, focus ring | 4.3:1 on page — AA large/UI only, NOT body text |
| `--accent-ink` | `#8A4A06` | Text links, small accent text | 6.0:1 on page — AA text |
| `--accent-soft` | `rgba(181,96,11,0.10)` | Tinted fills (hover, rare badge bg) | pair with `--accent-ink` text |
| `--line` | `#D8CCB4` | Hairlines, dividers, card frames | decorative |
| `--line-strong` | `#A08D6E` | Input borders, interactive outlines | 3.0:1 vs `--bg-surface` — AA UI |

### 2.2 Dark theme — « le cabinet » (intro, overlay menu, footer, dark sections, admin)

| Token | Hex | Role | Contrast notes |
|---|---|---|---|
| `--cab-bg` | `#14100C` | Deepest ground (admin page bg, intro) | base |
| `--cab-surface` | `#1D1812` | Panels, admin cards, footer | base |
| `--cab-raised` | `#262019` | Hover states, raised admin elements | base |
| `--cab-ink-1` | `#F1E9D8` | Primary text on dark | 14+:1 — AAA |
| `--cab-ink-2` | `#B8A88E` | Secondary text on dark | 7.8:1 on `--cab-bg` — AAA |
| `--cab-ink-3` | `#9A8A70` | Muted/meta on dark | 5.2:1 on `--cab-surface` — AA |
| `--cab-line` | `#3A3125` | Hairlines on dark | decorative |
| `--cab-gold` | `#CE9042` | Accent on dark grounds (or ancien): links, active states, chart primary | 6.4:1 on `--cab-surface` — AA text. Note: raw `--accent #B5600B` is only 4.1:1 on dark — use it for large graphics only; `--cab-gold` for text |

### 2.3 Semantic — derived from the stamps

| Token | Hex | Role | Contrast notes |
|---|---|---|---|
| `--ok` | `#2F6B4A` | Success text/icons — « vert Semeuse » (5c) | 5.5:1 on page — AA |
| `--ok-soft` | `#E5EDE3` | Success tint bg | with `--ok` text: AA |
| `--error` | `#A93A32` | Error text/icons — « rouge Semeuse » (10c), encre | 5.5:1 on page — AA |
| `--error-fill` | `#C0453C` | Filled danger buttons, très-rare badge | with `#FBF7EC` text: 4.7:1 — AA |
| `--error-soft` | `#F3E3DF` | Error tint bg | with `--error` text: AA |
| `--ok-dark` | `#7FBF9B` | Success on cabinet/admin | 8.2:1 on `--cab-surface` |
| `--error-dark` | `#E08A80` | Error on cabinet/admin | 6.8:1 on `--cab-surface` |
| `--focus` | `#B5600B` | Focus ring (light); `#CE9042` on dark | 4.3:1 / 6.4:1 — AA UI |

Warning states reuse `--accent-ink`/`--accent-soft` (no foreign yellow enters the palette). Info states reuse `--ink-2`. **Delete on sight:** `#4ade80`, `#3b82f6`, `#28a745`, `#dc3545`, and all ad-hoc `rgba(181,96,11,*)` — every one maps to a token above.

### 2.4 Charts (admin, Chart.js self-hosted)

Series order: `#CE9042` (gold), `#7FBF9B` (sage), `#E08A80` (brick), `#B8A88E` (parchment), `#8C9BA5` (ardoise, reserve). Gridlines `#3A3125`, tick labels `--cab-ink-3`, tooltips on `--cab-raised`.

---

## 3. Typography

Four families, all Google Fonts, self-hosted as latin-subset woff2 in `static/fonts/` (download via gwfh / fonts.google.com download; total budget ≤ 360 KB). `font-display: swap` everywhere; preload only Cormorant 500 and EB Garamond 400.

| Family | Files (weights) | Role |
|---|---|---|
| **Cormorant Garamond** | 500, 600, 500-italic | Display: hero titles, page titles, section heads, big numerals |
| **EB Garamond** | 400, 400-italic, 500, 600 | Text: body copy, cartel labels (real small caps via `font-variant-caps: small-caps` — EB Garamond ships `smcp`; synthesized fallback is acceptable), oldstyle figures for card numbers |
| **Inter** | 400, 500, 600 | UI: form inputs, helper text, badges, toasts, tables, all of the admin (`font-variant-numeric: tabular-nums` for data) |
| **Caveat** | 400, 600 | Handwriting only: La Poste messages, signature line, contact card annotation. Replaces the never-loaded Dancing Script. Never letter-spaced, never below 1.25rem |

Fallback stacks: serif → `Georgia, 'Times New Roman', serif`; sans → `system-ui, -apple-system, 'Segoe UI', sans-serif`; script → `cursive`. **Remove** the `*{font-family}` universal selector; set the stack on `body` and let inheritance work (kills the 11 `font-family:inherit` workarounds).

### 3.1 Scale (base 16px; body bumped because Garamond runs small)

| Token | Size | Family/Weight | Line-height | Letter-spacing |
|---|---|---|---|---|
| `--t-hero` | `clamp(2.5rem, 6vw, 4.25rem)` | Cormorant 500 | 1.05 | -0.01em |
| `--t-h1` | `clamp(1.9rem, 4vw, 2.5rem)` | Cormorant 600 | 1.15 | -0.005em |
| `--t-h2` | `1.625rem` | Cormorant 600 | 1.2 | 0 |
| `--t-h3` | `1.3125rem` | EB Garamond 600 | 1.3 | 0 |
| `--t-lead` | `1.1875rem` | EB Garamond 400 | 1.65 | 0 |
| `--t-body` | `1.0625rem` (17px) | EB Garamond 400 | 1.6 | 0 |
| `--t-small` | `0.9375rem` | EB Garamond 400 / Inter 400 | 1.5 | 0 |
| `--t-caption` | `0.8125rem` | Inter 400 | 1.5 | +0.01em |
| `--t-cartel` | `0.875rem` | EB Garamond 500 small-caps | 1.4 | +0.08em |
| `--t-etiquette` | `0.75rem` | Inter 600 UPPERCASE | 1.3 | +0.14em |
| `--t-script` | `1.375rem` | Caveat 400 | 1.5 | 0 (never track script) |
| `--t-admin-data` | `0.875rem` | Inter 400/500, tabular-nums | 1.45 | 0 |

**Letter-spacing law:** the smaller the caps, the wider the tracking (+0.08em at 0.875rem small caps → +0.14em at 0.75rem uppercase — this is the « CARTE POSTALE » letterpress echo). Display serif tightens slightly at size. Body serif never tracked. Card numbers render as `N° 1024` in EB Garamond with `font-feature-settings: "onum"` on public pages; Inter lining tabular in admin tables.

Prose measure: `max-width: 65ch` on all long-form text (presentation, decouvrir).

---

## 4. Spacing, radius, shadow, border tokens

```css
:root {
  /* spacing — 4px base */
  --sp-1: 0.25rem; --sp-2: 0.5rem; --sp-3: 0.75rem; --sp-4: 1rem;
  --sp-5: 1.5rem; --sp-6: 2rem;   --sp-7: 3rem;    --sp-8: 4rem;
  --sp-9: 6rem;  --sp-10: 8rem;
  /* layout */
  --nav-h: 64px;               /* single source of the header offset */
  --container: 1200px; --container-wide: 1440px; /* admin */
  --gutter: var(--sp-5);       /* 16px (--sp-4) below 768px */
  /* radius — museum frames are nearly square */
  --r-1: 2px;   /* postcard frames, badges, tags */
  --r-2: 4px;   /* buttons, inputs */
  --r-3: 8px;   /* modals, toasts, admin cards */
  --r-pill: 999px; /* count pills, avatars */
  /* shadows — warm sepia, never pure black (light theme) */
  --shadow-1: 0 1px 2px rgba(43,33,24,.08);
  --shadow-2: 0 2px 8px rgba(43,33,24,.10), 0 1px 2px rgba(43,33,24,.06);
  --shadow-3: 0 12px 32px -8px rgba(43,33,24,.18), 0 2px 8px rgba(43,33,24,.08);
  --shadow-plate: 0 1px 1px rgba(43,33,24,.10), 0 6px 18px -6px rgba(43,33,24,.22); /* postcard at rest */
  --shadow-modal: 0 24px 64px -16px rgba(23,17,11,.45);
  /* borders */
  --hairline: 1px solid var(--line);
  /* double filet — the engraved signature detail (frames, section heads): */
  --filet: 0 0 0 1px var(--line), 0 0 0 5px var(--bg-mat), 0 0 0 6px var(--line);
}
```

Section rhythm: `--sp-9` (96px) between page sections desktop, `--sp-8` (64px) mobile. **One breakpoint system, everywhere:** 480 / 768 / 1024 / 1280. Navbar collapses below 1024.

Texture: one single paper-grain asset (tileable 200×200 PNG, ≤8 KB, 3% opacity overlay) allowed **only** on `--cab-bg` surfaces (intro, footer, overlay menu). Never on reading surfaces, never on light theme.

---

## 5. Component specs

### 5.1 Buttons
- **Primary** (`.btn-primary`): bg `--ink-1`, text `#F5EFE2` (13:1), Inter 600 `--t-etiquette` tracking +0.08em uppercase, height 48px (40px `.btn-sm`), padding 0 `--sp-5`, radius `--r-2`, `--shadow-1`. Hover: bg `#17110B`, translateY(-1px), `--shadow-2`, 160ms. Active: translateY(0), no shadow. On dark grounds: bg `--cab-gold`, text `#14100C` (6.4:1).
- **Secondary**: transparent, 1px `--line-strong` border, text `--ink-1`. Hover: border `--ink-1`, bg `rgba(43,33,24,.04)`.
- **Danger**: bg `--error-fill`, text `#FBF7EC` (4.7:1). Confirmation contexts only.
- **Tertiary/link**: `--accent-ink`, underline `text-decoration-thickness:1px; text-underline-offset:3px`; hover thickens to 2px + shifts to `--accent` — no color-only change.
- All: `:focus-visible { outline: 2px solid var(--focus); outline-offset: 2px }`. Disabled: opacity .45, no pointer events, never remove the label.

### 5.2 Inputs
Height 48px, bg `--bg-surface`, border 1px `--line-strong` (3:1 AA), radius `--r-2`, padding 0 `--sp-4`, Inter 400 1rem, placeholder `--ink-3`. Label above in `--t-etiquette` color `--ink-2`, margin-bottom `--sp-2`. Focus: border `--ink-1` + ring `0 0 0 3px var(--accent-soft)`. Error: border `--error` + message below in `--error` `--t-caption` with 14px icon, tied via `aria-describedby`. Textarea (message compose): Caveat 400 `--t-script` on faint ruled lines (`repeating-linear-gradient` every 2rem, `--line` at 40%) — writing on the card. **6-digit code:** six 52×64px cells, EB Garamond 600 1.5rem centered; first cell carries `autocomplete="one-time-code" inputmode="numeric"`; auto-advance, Backspace steps back, full-code paste distributes; filled cell border `--accent`.

### 5.3 Cards & the postcard frame (le passe-partout)
Every postcard image sits in a mat: bg `--bg-mat`, padding 10px (14px in modal), `box-shadow: var(--filet), var(--shadow-plate)`, radius `--r-1`, image radius 0. Image `object-fit: contain` on `--bg-well` ground (CPA ratios vary; never crop). Below, the **cartel**: `N° 1024` in `--t-cartel` `--ink-2`, title in EB Garamond 500 1rem `--ink-1` (2-line clamp), rarity badge right-aligned. Grid tile hover: translateY(-4px), shadow deepens to `--shadow-3`, image scales 1.02 inside the fixed mat, 320ms `--ease-out`; entire tile is one `<a>`/`<button>`, focus-visible shows the ring on the mat. Generic content cards (profile, stats): `--bg-surface`, `--hairline`, radius `--r-3`, `--shadow-1`, padding `--sp-5`.

### 5.4 Modal — « la vitrine » (single shared partial; delete both inline duplicates)
Scrim `rgba(23,17,11,.82)`. Desktop: centered panel `--bg-surface`, radius `--r-3`, `--shadow-modal`, max-width 920px, max-height 90vh; postcard in full passe-partout left/top, cartel + description + actions (flip, zoom, like, « Envoyer via La Poste ») right/below. Mobile <768px: full-screen sheet sliding up 320ms. Entry: scrim fades 200ms, panel fades+rises 12px 320ms `--ease-out`. Requirements: `role="dialog" aria-modal="true" aria-labelledby={title}`, focus trap, focus returns to the invoking tile on close, Escape + scrim click + 44×44px close button (top-right, real button). Arrow keys ←/→ move through the grid's cards without closing. Like: outline heart → fills `--error` (a red heart is a stamp color here) with 200ms scale 1→1.15→1; count beside it, `aria-pressed`.

### 5.5 Navbar
Desktop: fixed 64px (`--nav-h`), bg `rgba(252,250,243,.92)` + `backdrop-filter: blur(8px)`, bottom `--hairline`; gains `--shadow-1` after 8px scroll. Left: `Samathey.png` at 36px height, `alt="Collection Samathey — accueil"`. Center/right: text links (never icon-only) in `--t-etiquette` `--ink-2`; hover `--ink-1`; active page: `--ink-1` + a 24px-wide 2px `--accent` rule centered under the label. Right: search icon-button 44×44 (with `aria-label`), user avatar/« Connexion ». Skip link (`Aller au contenu`) as first focusable element, visible on focus. Mobile <1024px: 56px bar, burger 44×44 → full-screen « cabinet » overlay: bg `--cab-bg` + grain, links in Cormorant 500 1.75rem `--cab-ink-1`, staggered 40ms fade-up, close mirrors burger position; focus trapped while open; `body{overflow:hidden}`.

### 5.6 Footer
Bg `--cab-surface`, top border: gold double filet (`1px #8A6B3F` + 4px gap + `1px #8A6B3F`). `Samathey_blanc.png` + a faint circular postmark SVG watermark (`--cab-line`). Three columns (stack <768px): La Collection / La Poste & Compte / « Mentions légales · Confidentialité · Gérer les cookies · Contact » — legally required in France and currently absent. Text `--cab-ink-2`, links hover `--cab-gold`. Credit line « — A Z DATA Production 2025 — » in `--t-caption` `--cab-ink-3`.

### 5.7 Badges
- **Rarity — étiquettes:** radius `--r-1`, Inter 600 0.6875rem uppercase +0.1em, padding 3px 8px. `Commune`: transparent, 1px `--line-strong`, text `--ink-2`. `Rare`: bg `--accent-soft`, 1px `rgba(181,96,11,.35)`, text `--accent-ink`. `Très rare`: bg `--error-fill`, text `#FBF7EC` (4.7:1) — the 10c red reserved for the treasures. Never color-only: the label text is always present.
- **Count pill** (unread, likes): `--r-pill`, min 20px, bg `--accent`, white text, Inter 600 0.75rem; `aria-label="3 cartes non lues"`.
- **Member category:** always the display label (`Membre vérifié`), never raw slugs like `subscribed_verified`; outline style, `--ink-2`.

### 5.8 Toasts (replaces Django messages styling)
Container top-right desktop / bottom mobile, `aria-live="polite"` (`role="alert"` for errors), max 3 stacked. Toast: `--bg-surface`, radius `--r-3`, `--shadow-3`, 3px left rule + 16px icon in semantic color, title Inter 600 0.875rem + optional body `--t-caption`, 44px close. Enter: slide-in 12px + fade 240ms `--ease-out`; auto-dismiss 5s, paused on hover/focus; exit fade 200ms. Success « Carte envoyée » may show a 16px 5c-green postmark tick.

### 5.9 Skeleton loaders
Base `--bg-well`, radius matches target, shimmer: 1.4s linear gradient sweep (`rgba(255,254,249,.6)` band), `animation: none` under reduced motion. Postcard-tile skeleton = mat outline + image block (aspect 3:2) + 60%/35% label lines. Use while modal images and La Poste lists load; on browse, skeletons render during paginated fetches. Never a full-page fake loader — MIN_LOADING_TIME dies.

### 5.10 Pagination (server-side — mandatory, ~48 cards/page)
Centered row: « Précédente » / numbered links / « Suivante », EB Garamond oldstyle numerals 1rem, 40×40px targets. Current page: `--ink-1` filled square `--r-1`, cream numeral, `aria-current="page"`. Ellipsis in `--ink-3`. Above the grid: « 1 862 cartes — page 3 sur 39 » in `--t-cartel`. Query params compose (`?keywords=…&page=3`).

### 5.11 Consent banner (CNIL)
Bottom card `--bg-surface`, `--shadow-3`, radius `--r-3` (mobile full-width sheet): one sentence + « Accepter » (primary) / « Refuser » (secondary) / « Préférences » (link) — equal prominence per CNIL. GA loads only after consent; re-openable from footer « Gérer les cookies ».

---

## 6. Motion language

```css
--dur-1: 120ms;  /* micro: color, focus, icon */
--dur-2: 200ms;  /* fades, underlines, toggles */
--dur-3: 320ms;  /* entrances: cards, modal, menu */
--dur-4: 560ms;  /* theatrical: postcard flip, overlay menu bg */
--ease-out: cubic-bezier(0.22, 1, 0.36, 1);   /* entrances — objects settling */
--ease-in-out: cubic-bezier(0.65, 0, 0.35, 1); /* flip, curtains */
--ease-in: cubic-bezier(0.4, 0, 1, 1);         /* exits only */
```

**Laws.** Animate only `opacity` and `transform`. No infinite ambient loops on content pages (fish, particles, floating emoji: deleted). Stagger 40ms, capped at 8 items. Nothing bounces or overshoots — `ease-out-quint` settles, never springs. Content is never hidden pending JS: entrance animations live behind `@media (prefers-reduced-motion: no-preference)` and an `html.js` guard, so no-JS and reduced-motion users get everything at `opacity:1` instantly (fixes the `[class*="animate-"]{opacity:0}` trap).

**Page entrance:** `<main>` children fade-up 8px, 240ms, 40ms stagger. **Hover:** per component specs — lift + shadow, 160–320ms. **The flip (the signature gesture):** wrapper `perspective:1200px`; card `transform-style:preserve-3d`, faces `backface-visibility:hidden`, verso pre-rotated 180°; toggle rotates Y 180° over `--dur-4` `--ease-in-out` while the wrapper scales 1→1.03→1 and the plate shadow stretches at midpoint — the card physically lifts off the mat to turn. Trigger: « Voir le verso » button (`aria-pressed`, label swaps) or clicking the card; announce « Verso affiché » via visually-hidden `aria-live`. Reduced motion: 200ms crossfade. **Zoom:** explicit button opens zoom layer; wheel/buttons 1–3×, drag pan, double-tap 2.5× on touch; Escape closes.

**Intro (replaces the 3s fake loader, total ≤1.6s):** cabinet-dark ground fades in 200ms → circular postmark SVG (« COLLECTION SAMATHEY · CARTES POSTALES ANCIENNES ») draws via stroke-dashoffset 700ms `--ease-out` → « Collection Samathey » in Cormorant fades up 320ms → date-line in gold étiquette caps → hold ~400ms → whole overlay lifts like a curtain 480ms `--ease-in-out` revealing home. Any click/keypress skips instantly; visible « Passer » control; once per day via localStorage; reduced motion = 600ms static fade; no fake progress bars or invented status text; `?next=` validated server-side with `url_has_allowed_host_and_scheme`.

---

## 7. Per-page layout direction

**Accueil.** Full-bleed hero on `--cab-bg`: one large animated postcard (existing hero videos) in a floating passe-partout, `Samathey_blanc.png` above, hero title in Cormorant, one primary CTA « Parcourir la collection » + tertiary « La Poste ». Below, on vélin: « Pièces choisies » — a 3-up row of curator-picked cards with cartels, a numbers strip (« 1 862 cartes · depuis 1900 ») in big Cormorant oldstyle numerals, and a two-column invitation to La Poste with the two Semeuse stamps as illustration.

**Intro.** As storyboarded in §6 — a single centered composition on the cabinet ground, postmark + wordmark, skippable, never blocking.

**Parcourir + modal.** A gallery wall: sticky sub-header under the nav holding search, active-filter chips, result count in `--t-cartel`; server-paginated grid `repeat(auto-fill, minmax(240px,1fr))` gap `--sp-6` (2-col ≥480px, 1-col below) of matted tiles; working server-side sort/filter panel in a collapsible drawer; pagination §5.10. Modal is the vitrine of §5.4. No ambient animation anywhere on this page — the cards are the show.

**CP animées.** Same wall, dark variant: `--cab-bg` with grain, matted video tiles with a small `--cab-gold` play glyph in the cartel; click opens the shared vitrine modal playing video (`preload="none"`, poster from vignette). Kill the second modal system.

**Présentation.** Exhibition-catalog essay page: 65ch column, Cormorant H1 + lead paragraph, EB Garamond body, timeline as a vertical hairline with postmark-dot milestones and years in Cormorant numerals, one full-width matted archival image as a breather, double-filet section rules.

**Découvrir.** « Salle des tableaux »: the six framed paintings on a quiet `--bg-well` ground, each a real `<button>` with visible cartel below (title always present, not hover-only); opens the shared modal with a self-hosted or youtube-nocookie embed behind consent. The rickroll placeholder is retired.

**Contact.** A writing desk: left, a short invitation; right, an interactive postcard verso (the `Cpa_Vierge` layout) — message area in Caveat on ruled lines, sender email + name fields (added to the form), and a stamp corner where choosing the 5c/10c actually works, with the character allowance stated up front and counted live via `aria-live`. Success replaces the card with a postmarked « Bien reçue » state — dismissible, auto-clearing, never a permanent overlay.

**La Poste.** The correspondence room, light theme (dark reserved for cabinet moments): tabs Reçues / Envoyées / Le Mur in `--t-etiquette` with `--accent` underline, unread pill live-updated; received cards stack as slightly rotated (±1°) matted minis that straighten on hover; compose is a full vitrine modal — pick a card (searchable, paginated picker, `?to=`/`?postcard=` prefills honored), write in Caveat, affix the 5c/10c stamp (drag or click, 44-char limit for 5c explained *before* truncation, switching stamps warns instead of silently cutting), sign, send; sent confirmation = postmark stamp animation 560ms, list updates without reload; Escape/backdrop asks confirmation when a draft exists. All user content escaped via `textContent` rendering.

**Profil.** Member's cabinet drawer: header card with avatar (`--r-pill`), display-label category badge, signature preview in Caveat; stat cartels (cartes envoyées/reçues/aimées) as small `--bg-surface` cards with Cormorant numerals; tabs for Activité / Connexions / Réglages as sub-sections of working routes; connection rows with functioning « Écrire » deep-link into La Poste.

**Auth (connexion / inscription / code / mot de passe).** One shared centered layout: 420px `--bg-surface` card, radius `--r-3`, `--shadow-2`, small Samathey logo, on a vélin ground with a faint postmark watermark; a 3-step étiquette tracker (Inscription · Vérification · Mot de passe) on all funnel steps including step 1 (register joins the family: same dark-on-cream inputs, same primary button); code screen uses §5.2 cells with resend link + countdown; password screen's checklist mirrors the server's actual validators; login gains « Mot de passe oublié ? »; errors in `--error` with `role="alert"`.

**Admin dashboard.** The conservator's back-office on the cabinet palette (`--cab-*` tokens, Inter throughout, `--container-wide`): left rail nav 240px (collapsible to icons), KPI cartels in a 4-up row — gold Cormorant numerals on `--cab-surface`, delta arrows in `--ok-dark`/`--error-dark` — charts per §2.4 with self-hosted pinned Chart.js, dense tables (Inter 0.875rem tabular, 40px rows, sticky header, hover `--cab-raised`), all dynamic strings escaped. CSS in `<head>` (no more body-bottom FOUC). Professional, quiet, unmistakably the same brand after dark.

---

## 8. What makes this feel expensive rather than generic

1. **A palette with provenance** — every color traceable to an artifact (card stock, sepia ink, brand ochre, the two Semeuse stamps as semantic colors). No Tailwind/Bootstrap defaults anywhere.
2. **Real typographic craft**: true small caps, oldstyle figures, tracking that widens as caps shrink, a 65ch measure, a Garamond duet with a French story — details visitors feel without naming.
3. **The passe-partout + cartel system**: images are *mounted and labeled*, not dumped into rounded cards — the single strongest museum signal, applied identically from grid to modal to La Poste.
4. **Engraved ornament, not applied decoration**: hairlines, the double filet, the postmark motif recurring at intro/footer/empty states — one motif, disciplined, instead of emoji dust, fish and particles.
5. **One theatrical gesture** (the flip) executed with physical conviction (perspective, lift, shadow travel), everything else settling in under 350ms with no bounce.
6. **Warm sepia shadows** (`rgba(43,33,24,…)`) — grey-black shadows on cream instantly read as template; tinted shadows read as printed matter.
7. **Near-square radii**: 2–4px frames photograph like mounted prints; 16px rounded cards photograph like a SaaS dashboard.
8. **Honest speed as luxury**: no fake loaders, no artificial delays, server pagination, skeletons only when something real is loading. A museum never makes you queue at an empty door.
9. **Text you can select**, focus states that were designed, reduced-motion and keyboard paths that work — accessibility finish is part of the perceived price.
10. **Banned tells**: gradient text, glassmorphism on content, spring easings, emoji as ornament, raw category slugs, default-blue links, Comic-Sans-class cursive fallbacks.

---

## 9. Implementation guardrails (ties spec to the audit)

- All tokens live in `:root` in a rebuilt `base.css`; delete orphan `browse.css`, `contact.css`, `home.css`, `presentation.css`, `gallery.css` conflicts, `browse.js`, `gallery.js`, dead `main.js` sections, `admin_sync_ovh.html`, empty `postcard_modal.html` (rebuild it as the real shared partial).
- Per-page CSS moves to cacheable files under `static/css/pages/` loaded via `{% block extra_css %}` in `<head>`; JS via `extra_js` with `defer`. Fix `{% block page_title %}` by moving it out of the navbar include; give every page a unique `<title>` + meta description + OG tags in a `{% block meta %}`.
- Fonts: `@font-face` blocks at the top of `base.css`, `woff2` only, latin subset, preload Cormorant 500 + EB Garamond 400 in `base.html`.
- Remove `user-select:none` and the contextmenu block; protect images instead with the existing rarity gating done server-side (very-rare URLs must not reach the anonymous DOM).
- Accessibility floor: skip link, `:focus-visible` ring token, `aria-live` toast region, dialog semantics + focus traps on every modal, `prefers-reduced-motion` honored globally, meaningful alt text (`alt="Carte N° 1024 — Pont d'Avignon, recto"`).
