# CACHET v1.1 — Final design system, « Le Postier / Collection Samathey »

Base: **Cachet** (Concept 1). Grafts: from **Cimaise** — native `<dialog>` modal, the « one money-action per view » rule, the 48px filet-double heading monogram, the modal « unboxing beat »; from **Papeterie Postale** — the « coup de tampon » like animation, verso-ruled textareas, the CVD-validated admin chart palette, the deterministic « carte du jour », the dentelure footer edge, and the « max one postal motif per view » rationing law.

Stack: Django templates + hand-written CSS + vanilla JS. No build step, no CDN. All fonts self-hosted woff2.

---

## 1. Concept

The site is the catalogue of a permanent exhibition. Postcards hang on a warm vélin wall, matted in a passe-partout, labeled with a cartel (number, title, rarity in letter-spaced small caps). The palette is extracted from the artifacts: cream card stock, sepia ink, the brand ochre #B5600B, and the two Semeuse stamps — 5c green and 10c red become success and error, so even system feedback speaks the collection's language. Dark is used as museums use it — for cabinet moments only: intro, overlay menu, footer, admin. One theatrical gesture (the recto/verso flip), one interaction jewel (the postmark stamping on a like), everything else settles quietly in under 350ms. Restraint is the luxury.

**Rationing law (grafted from Papeterie):** the postal motif set — circular postmark (cachet), dentelure edge, verso ruling — appears **at most once per view**, never combined.

---

## 2. Color tokens

All in `:root` of `static/css/tokens.css`, loaded first. Contrast per WCAG 2.1 (AA text ≥4.5:1; AA UI/large ≥3:1).

### 2.1 Light — « la salle » (all public pages)

| Token | Hex | Role |
|---|---|---|
| `--bg-page` | `#F5EFE2` | Page background (warm vélin) |
| `--bg-surface` | `#FCFAF3` | Cards, modals, inputs, navbar |
| `--bg-well` | `#EDE5D2` | Recessed zones, skeleton base, verso ground |
| `--bg-mat` | `#FFFEF9` | **Reserved for the passe-partout mat only** — the brightest surface on the site, so artifacts sit one step brighter than the wall (Cimaise's gallery-lighting trick) |
| `--ink-1` | `#2B2118` | Primary text/headings — 13.7:1 on page (AAA) |
| `--ink-2` | `#5B4A38` | Secondary text, cartels — 7.4:1 (AAA) |
| `--ink-3` | `#7A6A55` | Captions, meta, placeholders — 4.6:1 (AA). On `--bg-well` use `--ink-2` or ≥1.25rem |
| `--ink-faint` | `#A29377` | Decorative rules/watermarks only — never text |
| `--accent` | `#B5600B` | Brand ochre: icons, large display accents, active underlines, focus ring — 4.3:1, UI/large only, never body text |
| `--accent-ink` | `#8A4A06` | Text links, small accent text — 6.0:1 (AA) |
| `--accent-soft` | `rgba(181,96,11,.10)` | Tinted fills; pair with `--accent-ink` text |
| `--line` | `#D8CCB4` | Hairlines, dividers, frames |
| `--line-strong` | `#A08D6E` | Input borders — 3.0:1 vs surface (AA UI) |

### 2.2 Dark — « le cabinet » (intro, overlay menu, footer, admin)

| Token | Hex | Role |
|---|---|---|
| `--cab-bg` | `#14100C` | Deepest ground |
| `--cab-surface` | `#1D1812` | Panels, admin cards, footer |
| `--cab-raised` | `#262019` | Hover/raised |
| `--cab-ink-1` | `#F1E9D8` | Primary text — 14+:1 |
| `--cab-ink-2` | `#B8A88E` | Secondary — 7.8:1 on bg |
| `--cab-ink-3` | `#9A8A70` | Meta — 5.2:1 on surface |
| `--cab-line` | `#3A3125` | Hairlines |
| `--cab-gold` | `#CE9042` | Accent on dark: links, active states — 6.4:1 on surface (AA). Raw `--accent` is 4.1:1 on dark: large graphics only |

### 2.3 Semantic — the Semeuse stamps

| Token | Hex | Role |
|---|---|---|
| `--ok` | `#2F6B4A` | Success (vert Semeuse 5c) — 5.5:1 |
| `--ok-soft` | `#E5EDE3` | Success tint bg |
| `--error` | `#A93A32` | Error text/icons (rouge Semeuse 10c) — 5.5:1 |
| `--error-fill` | `#C0453C` | Danger buttons, très-rare badge; with `#FBF7EC` text 4.7:1 |
| `--error-soft` | `#F3E3DF` | Error tint bg |
| `--ok-dark` / `--error-dark` | `#7FBF9B` / `#E08A80` | Semantics on cabinet — 8.2:1 / 6.8:1 |
| `--focus` | `#B5600B` light / `#CE9042` dark | 2px `:focus-visible` outline + 2px offset, everywhere |

Warnings reuse `--accent-ink`/`--accent-soft`; info reuses `--ink-2`. **Delete on sight:** `#4ade80`, `#3b82f6`, `#28a745`, `#dc3545`, all ad-hoc `rgba(181,96,11,*)`.

### 2.4 Admin charts (grafted from Papeterie — CVD-validated)

Chart.js self-hosted, version-pinned. Categorical series in **fixed slot order, never cycled, never repainted when a filter removes a series**: 1 `#3987E5` blue · 2 `#D95926` orange · 3 `#199E70` green · 4 `#C98500` gold · 5 `#D55181` magenta. All five pass lightness band, chroma floor, adjacent-pair CVD separation (worst ΔE 8.4) and ≥3:1 vs surface `#1D1812`; first three pass all-pairs — cap scatter/dot maps at 3 series, fold the rest into « Autres ». Sequential ramps: blue only, light→dark. Chart text always `--cab-ink-*`, never a series color. Lines 2px; gridlines `#3A3125`; tooltips on `--cab-raised`; ≥2 series always get a legend. Stat-tile deltas use `--ok-dark`/`--error-dark` with ▲▼ icon + label, never color alone.

---

## 3. Typography

Four families, Google Fonts, self-hosted latin-subset woff2 in `static/fonts/`, `@font-face` at top of `tokens.css`, `font-display: swap`, total ≤360 KB. Preload Cormorant Garamond 500 + EB Garamond 400 in `base.html`.

| Family | Files | Role |
|---|---|---|
| **Cormorant Garamond** | 500, 600, 500-italic | Display: hero, page/section titles, big numerals |
| **EB Garamond** | 400, 400-italic, 500, 600 | Body, cartels (real small caps via `font-variant-caps: small-caps`), oldstyle figures |
| **Inter** | 400, 500, 600 | UI: forms, badges, toasts, tables, all admin (`font-variant-numeric: tabular-nums`) |
| **Caveat** | 400, 600 | Handwriting only: La Poste messages, signatures, contact card. Never tracked, never below 1.25rem |

Fallbacks: `Georgia, 'Times New Roman', serif` / `system-ui, -apple-system, 'Segoe UI', sans-serif` / `cursive`. **No `*` font-family selector** — set on `body`, inherit.

### Scale (base 16px)

| Token | Size | Family/weight | LH | Tracking |
|---|---|---|---|---|
| `--t-hero` | `clamp(2.5rem, 6vw, 4.25rem)` | Cormorant 500 | 1.05 | −0.01em |
| `--t-h1` | `clamp(1.9rem, 4vw, 2.5rem)` | Cormorant 600 | 1.15 | −0.005em |
| `--t-h2` | `1.625rem` | Cormorant 600 | 1.2 | 0 |
| `--t-h3` | `1.3125rem` | EB Garamond 600 | 1.3 | 0 |
| `--t-lead` | `1.1875rem` | EB Garamond 400 | 1.65 | 0 |
| `--t-body` | `1.0625rem` | EB Garamond 400 | 1.6 | 0 |
| `--t-small` | `0.9375rem` | EB Garamond / Inter 400 | 1.5 | 0 |
| `--t-caption` | `0.8125rem` | Inter 400 | 1.5 | +0.01em |
| `--t-cartel` | `0.875rem` | EB Garamond 500 small-caps | 1.4 | +0.08em |
| `--t-etiquette` | `0.75rem` | Inter 600 UPPERCASE | 1.3 | +0.14em |
| `--t-script` | `1.375rem` | Caveat 400 | 1.5 | 0 |
| `--t-admin-data` | `0.875rem` | Inter 400/500 tabular | 1.45 | 0 |

**Laws:** the smaller the caps, the wider the tracking (+0.08em small caps → +0.14em uppercase — the « CARTE POSTALE » letterpress echo). Serif never tracked positive. Card numbers: `N° 1024`, EB Garamond `font-feature-settings: "onum"` on public pages; Inter lining tabular in admin. Prose measure `max-width: 65ch`.

---

## 4. Space, radius, shadow, borders

```css
:root {
  --sp-1:.25rem; --sp-2:.5rem; --sp-3:.75rem; --sp-4:1rem; --sp-5:1.5rem;
  --sp-6:2rem; --sp-7:3rem; --sp-8:4rem; --sp-9:6rem; --sp-10:8rem;
  --nav-h:64px; --container:1200px; --container-wide:1440px;
  --gutter:var(--sp-5); /* --sp-4 below 768px */
  --r-1:2px;   /* frames, badges, chips */
  --r-2:4px;   /* buttons, inputs */
  --r-3:8px;   /* modals, toasts, cards */
  --r-pill:999px;
  /* warm sepia shadows — never grey-black */
  --shadow-1:0 1px 2px rgba(43,33,24,.08);
  --shadow-2:0 2px 8px rgba(43,33,24,.10),0 1px 2px rgba(43,33,24,.06);
  --shadow-3:0 12px 32px -8px rgba(43,33,24,.18),0 2px 8px rgba(43,33,24,.08);
  --shadow-plate:0 1px 1px rgba(43,33,24,.10),0 6px 18px -6px rgba(43,33,24,.22);
  --shadow-modal:0 24px 64px -16px rgba(23,17,11,.45);
  --hairline:1px solid var(--line);
  --filet:0 0 0 1px var(--line),0 0 0 5px var(--bg-mat),0 0 0 6px var(--line); /* double filet box, frames */
}
```

**Filet-double monogram (grafted from Cimaise):** under every page h1 and in the footer, a 48px-wide double rule — 1px `--ink-1` over a 3px gap over 1px `--line`. The system's signature mark alongside the postmark.

Section rhythm: `--sp-9` desktop, `--sp-8` mobile. **One breakpoint system everywhere: 480 / 768 / 1024 / 1280.** Navbar collapses <1024.

Texture: one tileable 200×200 paper-grain PNG (≤8 KB) at 3% opacity, **only** on `--cab-bg` surfaces. Never on reading surfaces.

---

## 5. Components

Global: `:focus-visible { outline:2px solid var(--focus); outline-offset:2px }`. Remove `user-select:none` and the contextmenu block; protect rare images server-side instead (very-rare URLs never reach the anonymous DOM).

### 5.1 Buttons
- **Primary:** bg `--ink-1`, text `#F5EFE2` (13:1), Inter 600 `--t-etiquette` +0.08em uppercase, height 48px (40px `.btn-sm`), padding 0 `--sp-5`, `--r-2`, `--shadow-1`. Hover: bg `#17110B`, translateY(−1px), `--shadow-2`, 160ms. On dark: bg `--cab-gold`, text `#14100C`. **One money-action per view (Cimaise rule):** exactly one primary button per screen — « Envoyer », « Parcourir la collection », « Valider ».
- **Secondary:** transparent, 1px `--line-strong`, text `--ink-1`. Hover: border `--ink-1`, bg `rgba(43,33,24,.04)`.
- **Danger:** bg `--error-fill`, text `#FBF7EC`. Confirmation contexts only.
- **Tertiary/link:** `--accent-ink`, underline 1px, `text-underline-offset:3px`; hover thickens to 2px + shifts to `--accent`.
- Disabled: opacity .45, no pointer events. All targets ≥44×44px.

### 5.2 Inputs
Height 48px, bg `--bg-surface`, 1px `--line-strong`, `--r-2`, padding 0 `--sp-4`, Inter 400 1rem, placeholder `--ink-3`. Label above in `--t-etiquette` `--ink-2`, margin-bottom `--sp-2`. Focus: border `--ink-1` + `box-shadow:0 0 0 3px var(--accent-soft)`. Error: border `--error` + message in `--error` `--t-caption` with 14px icon, `aria-describedby` + `aria-invalid`.
**Verso-ruled textarea (Papeterie graft):** message textareas render Caveat `--t-script` over `repeating-linear-gradient(transparent 0 1.85em, var(--line) 1.85em calc(1.85em + 1px))` with `line-height:1.85em` locked to the rules — writing on the card.
**6-digit code:** six 52×64px cells, EB Garamond 600 1.5rem centered; first cell `autocomplete="one-time-code" inputmode="numeric"`; auto-advance, Backspace steps back, paste distributes; filled border `--accent`.

### 5.3 Postcard frame — le passe-partout + cartel
Every postcard: mat bg `--bg-mat`, padding 10px (14px in modal), `box-shadow: var(--filet), var(--shadow-plate)`, radius `--r-1`, image radius 0, `object-fit: contain` on `--bg-well` (never crop a CPA), `loading="lazy" decoding="async"` + width/height. Below, the **cartel**: `N° 1024` in `--t-cartel` `--ink-2`, title EB Garamond 500 1rem `--ink-1` (2-line clamp), rarity badge right. Tile hover: translateY(−4px), `--shadow-3`, image scales 1.02 inside the fixed mat, 320ms `--ease-out`. Whole tile is one `<a>`; focus ring on the mat. Generic cards: `--bg-surface`, `--hairline`, `--r-3`, `--shadow-1`, padding `--sp-5`.
**Like « coup de tampon » (Papeterie graft):** heart button on the mat corner, 36px, outline `--ink-3`. On like, the postmark SVG stamps onto the mat corner: scale 1.4→0.96→1, opacity 0→.85, 320ms `--ease-out`, in `--error` ink (the 10c red); heart fills simultaneously; count ticks up with a 6px rise; `aria-pressed`. Unlike: 200ms fade. This is the site's one interaction jewel — nothing else may imitate it.

### 5.4 Modal — « la vitrine » (one shared partial; both inline duplicates deleted)
**Native `<dialog>` (Cimaise graft):** `showModal()` provides focus trap + Esc; add `aria-labelledby`, backdrop `rgba(23,17,11,.82)` via `::backdrop`, body scroll lock, focus return to the invoking tile, 44×44 close button top-right, scrim-click close (with dirty-draft confirm in compose). Panel: `--bg-surface`, `--r-3`, `--shadow-modal`, max-width 920px, max-height 90vh. Desktop: postcard in full passe-partout left, cartel + description + actions right (flip, zoom, like, « Envoyer via La Poste » — the `?postcard=` deep-link revived). Mobile <768px: full-screen sheet sliding up 320ms. Entry: scrim fades 200ms; panel fades + rises 12px, 320ms; **unboxing beat (Cimaise graft):** the artifact inside fades in 60ms after its frame. Arrow keys ←/→ traverse the grid without closing. Zoom: explicit button; wheel/buttons 1–3×, drag pan, double-tap 2.5×; Esc closes zoom layer first. Data comes from the gated detail endpoint (rarity-bypass fix).

### 5.5 Navbar
Desktop: fixed 64px, bg `rgba(252,250,243,.92)` + `backdrop-filter: blur(8px)`, bottom hairline; `--shadow-1` after 8px scroll. Left: `Samathey.png` 36px, `alt="Collection Samathey — accueil"`. Links (words, never icon-only) in `--t-etiquette` `--ink-2`, hover `--ink-1`; active: `--ink-1` + 24px-wide 2px `--accent` rule under the label. Right: search icon-button 44×44 with `aria-label`, La Poste unread pill, avatar/« Connexion ». Skip link « Aller au contenu » first-focusable, visible on focus. Mobile <1024px: 56px bar, 44×44 burger with `aria-expanded` → full-screen cabinet overlay: `--cab-bg` + grain, links Cormorant 500 1.75rem `--cab-ink-1`, 40ms staggered fade-up, focus trapped, Esc closes, `body{overflow:hidden}`.

### 5.6 Footer
`--cab-surface`. **Top edge: dentelure (Papeterie graft)** — punched half-circle strip via `radial-gradient(circle at 5px 0, transparent 3px, var(--cab-surface) 3px)` tiled 10px on an 8px strip (its one sanctioned appearance per view). `Samathey_blanc.png` + faint circular postmark watermark in `--cab-line`. Three columns (stack <768px): La Collection / La Poste & Compte / « Mentions légales · Confidentialité · Gérer les cookies · Contact » (legally required, currently absent). Text `--cab-ink-2`, hover `--cab-gold`. Credit « — A Z DATA Production 2025 — » in `--t-caption` `--cab-ink-3`.

### 5.7 Badges
Rarity — `--r-1`, Inter 600 0.6875rem uppercase +0.1em, padding 3px 8px. **Commune:** transparent, 1px `--line-strong`, text `--ink-2`. **Rare:** bg `--accent-soft`, 1px `rgba(181,96,11,.35)`, text `--accent-ink`. **Très rare:** bg `--error-fill`, text `#FBF7EC` — the 10c red reserved for treasures. Label text always present, never color-only. Count pill: `--r-pill`, min 20px, bg `--accent`, white Inter 600 0.75rem, `aria-label="3 cartes non lues"`. Member category: display label (« Membre vérifié »), never raw slugs.

### 5.8 Toasts
Container top-right desktop / bottom mobile, `aria-live="polite"` (`role="alert"` errors), max 3. Toast: `--bg-surface`, `--r-3`, `--shadow-3`, 3px left rule + 16px icon in semantic color, title Inter 600 0.875rem, 44px close. Enter: slide 12px + fade 240ms; auto-dismiss 5s (errors persist), paused on hover/focus.

### 5.9 Skeletons
Base `--bg-well`, radius matches target, 1.4s gradient sweep (`rgba(255,254,249,.6)`); static under reduced motion. Postcard skeleton = mat outline + 3:2 block + 60%/35% lines. Never a full-page fake loader — `MIN_LOADING_TIME` and both forced overlays die.

### 5.10 Pagination (server-side, mandatory — 48/page, divisible by 2/3/4 columns)
Centered: « Précédente » / numbered 40×40 links / « Suivante », EB Garamond oldstyle numerals; current = `--ink-1` filled square `--r-1`, cream numeral, `aria-current="page"`. Real `<a href="?page=n">` preserving query params. Above the grid: « 1 862 cartes — page 3 sur 39 » in `--t-cartel`.

### 5.11 Consent (CNIL)
Bottom card `--bg-surface`, `--shadow-3`, `--r-3`: one sentence + « Accepter » / « Refuser » / « Préférences » at equal prominence. GA loads only after consent; re-openable from footer.

---

## 6. Motion

```css
--dur-1:120ms; --dur-2:200ms; --dur-3:320ms; --dur-4:560ms;
--ease-out:cubic-bezier(.22,1,.36,1);
--ease-in-out:cubic-bezier(.65,0,.35,1);
--ease-in:cubic-bezier(.4,0,1,1); /* exits only */
```

**Laws.** Animate only `opacity`/`transform`. No infinite ambient loops (fish, particles, emoji, dust: deleted). Stagger 40ms, cap 8 items. Nothing bounces. Content visible by default: entrance animations behind `@media (prefers-reduced-motion: no-preference)` and an `html.js` guard — the `[class*="animate-"]{opacity:0}` trap is abolished. One reduced-motion block zeroes durations globally.

**Page entrance:** `<main>` children fade-up 8px, 240ms, 40ms stagger. **The flip:** wrapper `perspective:1200px`; card `transform-style:preserve-3d`, faces `backface-visibility:hidden`, verso pre-rotated 180°; rotateY 180° over 560ms `--ease-in-out` while the wrapper scales 1→1.03→1 and the plate shadow stretches at midpoint — the card lifts off the mat to turn. Trigger: « Voir le verso » button (`aria-pressed`) or clicking the card; announce « Verso affiché » via visually-hidden `aria-live`. Reduced motion: 200ms crossfade. **The like:** §5.3 coup de tampon.

**Intro (≤1.6s, replaces the 3s fake loader):** cabinet ground fades 200ms → postmark SVG (« COLLECTION SAMATHEY · CARTES POSTALES ANCIENNES ») draws via stroke-dashoffset 700ms → « Collection Samathey » Cormorant fades up 320ms → gold date-line → hold ~400ms → overlay lifts 480ms revealing home. Any click/key skips; visible « Passer »; once per day via localStorage; reduced motion = 600ms static fade; no fake progress; `?next=` validated with `url_has_allowed_host_and_scheme`.

---

## 7. Per-page direction

**Accueil.** Full-bleed hero on `--cab-bg`: **« La carte du jour » (Papeterie graft — deterministic date-seeded pick, replacing `order_by('?')` and per-request video probing)** in a floating passe-partout, `Samathey_blanc.png` above, Cormorant hero title, one primary « Parcourir la collection » + tertiary « La Poste ». Below on vélin: « Pièces choisies » 3-up with cartels, a numbers strip (« 1 862 cartes · depuis 1900 ») in Cormorant oldstyle numerals, a two-column La Poste invitation illustrated by the two Semeuse stamps.

**Parcourir.** Sticky sub-header under nav: search, active-filter chips (dismissible), result count in `--t-cartel`; **working** server-side sort/filter in a collapsible drawer; grid `repeat(auto-fill,minmax(240px,1fr))` gap `--sp-6` (2-col ≥480, 1 below) of matted tiles; pagination §5.10; skeletons during navigation. No ambient animation — the cards are the show.

**CP animées.** Same wall, dark variant: `--cab-bg` + grain, matted video tiles with `--cab-gold` play glyph in the cartel; shared vitrine modal plays video (`preload="none"`, poster from vignette; stored `has_animation` flag, no disk scans). Second modal system deleted.

**Présentation.** 65ch column, Cormorant h1 + filet-double monogram, EB Garamond `--t-lead` opening, timeline as vertical hairline with postmark-dot milestones and Cormorant-numeral years, one full-width matted archival image as a breather.

**Découvrir.** Six framed paintings on `--bg-well`, each a real `<button>` with visible cartel (titles never hover-only); shared modal with youtube-nocookie behind consent. Rickroll retired.

**Contact.** Writing desk: left, short invitation; right, interactive postcard verso — verso-ruled Caveat message area, sender email + name fields (added), 5c/10c stamp corner where **both** stamps work, character allowance stated up front with live `aria-live` counter. Success: postmarked « Bien reçue » state — dismissible, never a permanent overlay.

**La Poste.** Light theme. Tabs Reçues / Envoyées / Le Mur in `--t-etiquette` with `--accent` underline, unread pill live. Received cards as slightly rotated (±1°) matted minis that straighten on hover; message renders in Caveat over verso ruling with the 5c/10c stamp top-right. Compose = vitrine modal: searchable paginated card picker (honors `?to=`/`?postcard=`), write in Caveat, choose stamp with limits shown *before* choice (10c→5c switch warns, never silently truncates), sign, send → postmark strike 560ms, list updates in place (no `location.reload()`). Esc/backdrop confirms when a draft exists. All user content via `textContent`.

**Profil.** Header card: avatar `--r-pill`, display-label badge, Caveat signature preview; stat cartels (envoyées/reçues/aimées) with Cormorant numerals; tabs Activité / Connexions / Réglages on one working template (fixes the 500-ing routes); « Écrire » deep-links to `/la-poste/?to=`.

**Auth.** One centered 420px `--bg-surface` card, `--r-3`, `--shadow-2`, small logo, vélin ground with faint postmark watermark; 3-step étiquette tracker (Inscription · Vérification · Mot de passe) on all funnel steps — register joins the house style; code screen per §5.2 with resend + countdown; password checklist mirrors the server's actual validators; login gains « Mot de passe oublié ? »; errors `--error` with `role="alert"`.

**Admin.** Cabinet palette, Inter throughout, `--container-wide`: 240px left rail (collapsible), 4-up KPI cartels — gold Cormorant numerals on `--cab-surface`, deltas `--ok-dark`/`--error-dark` with ▲▼ + label — charts per §2.4, dense tables (Inter 0.875rem tabular, 40px rows, sticky header, hover `--cab-raised`), all dynamic strings via `textContent` (XSS fix), CSS in `<head>` (FOUC fix).

---

## 8. Why this reads expensive

1. Palette with provenance — every color traceable to an artifact; no framework defaults. 2. Real typographic craft: true small caps, oldstyle figures, tracking that widens as caps shrink, 65ch measure. 3. The passe-partout + cartel, applied identically grid → modal → La Poste, with the mat the brightest surface in the room. 4. Engraved ornament: hairlines, double filet, one postmark motif — rationed, never combined. 5. One theatrical gesture (flip) + one jewel (coup de tampon); everything else settles <350ms. 6. Warm sepia shadows, near-square 2–4px radii. 7. Honest speed: no fake loaders, server pagination, real skeletons. 8. Finish: designed focus states, reduced-motion and keyboard paths, selectable text.

**Banned tells:** gradient text, glassmorphism on content, spring easings, emoji ornament, raw slugs, default-blue links, pure-black shadows, pill buttons on content.

## 9. Implementation guardrails

- File order in `<head>`: `tokens.css` → `base.css` → `components.css` → `{% block extra_css %}` per-page `pages/*.css`; JS via `{% block extra_js %}` with `defer`. All 16 inline `<style>` blocks migrate out.
- Delete: orphan `browse.css`, `contact.css`, `home.css`, `presentation.css`, `gallery.css`, `browse.js`, `gallery.js`, dead `main.js` sections, `admin_sync_ovh.html`; rebuild empty `postcard_modal.html` as the single shared partial. Shared partials: `partials/modal.html`, `partials/postcard_frame.html`, `partials/pagination.html`, `partials/badge.html`.
- Fix `{% block page_title %}` by moving it out of the navbar include; every page gets unique `<title>`, meta description, OG tags via `{% block meta %}`.
- Accessibility floor: skip link, `:focus-visible` token, `aria-live` toast region, `<dialog>` semantics + focus return on every modal, `prefers-reduced-motion` honored globally, alt pattern « Carte N° 1024 — Pont d'Avignon, recto », 44px touch targets, unified 480/768/1024/1280 breakpoints.