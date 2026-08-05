# Le Postier — Shared Layout & Global Assets Audit

Project root: `C:/Users/mathe/Documents/CODING/Empire/le-postier`. All paths below relative to root unless absolute. Line counts: base.html = 42, navbar.html = 865, postcard_modal.html = 0 (empty), base.css = 319, main.js = 133, browse.js = 284, gallery.js = 0.

## 1. base.html (templates/base.html, 42 lines)

Minimal skeleton, `lang="fr"` (base.html:3).

**Head (lines 4–19):**
- charset + viewport meta only. **No meta description, no Open Graph/Twitter cards, no canonical, no theme-color** — nothing for SEO/social.
- Favicon: `images/Fav_icone.png` declared with wrong MIME `type="image/x-icon"` (base.html:7).
- Single stylesheet: `css/base.css` (base.html:8), then `{% block extra_css %}` (base.html:9).
- `<title>` block defaults to "Collection Samathey" (base.html:10). Only home.html:5 overrides `block title` — with identical text. **Every page on the site has the same `<title>`.**
- Google Analytics gtag `G-YZX5PNSJZG` loaded unconditionally with inline config script (base.html:12–19). **No consent banner exists anywhere** — a GDPR/CNIL problem for a French site.

**Body (lines 21–42):**
- `{% include 'partials/navbar.html' %}` (base.html:22)
- Django messages: `#messages-container` with `.alert.alert-{tag}` divs (base.html:24–32); no `aria-live`/`role="alert"`.
- `{% block content %}` (base.html:34)
- Footer: hardcoded `<p>- A Z DATA Production 2025 -</p>` (base.html:36–38) — no links, no sitemap, no legal mentions (mentions légales are legally required in France).
- `js/main.js` loaded at end of body (base.html:40), then `{% block extra_js %}` (base.html:41).

**Block structure:** `extra_css`, `title`, `content`, `extra_js`. That's all. No `body_class`, no `meta` block, no hero/header block.

**Duplicate base:** `templates/admin_sync_ovh.html` is a byte-for-byte copy of base.html (lines 1–43 identical, incl. GA at admin_sync_ovh.html:13–19 and main.js at :40). No view references it (grep for `admin_sync_ovh` in core/ returns nothing) — orphan file.

**Bypassing base:** `templates/intro.html` is a standalone full HTML document (own `<style>` at intro.html:8, own `<script>` at intro.html:204, no navbar/footer), rendered by `core/views.py:1202`. It repeats the font stack (intro.html:19) and its own dark palette (intro.html:12).

## 2. Navbar (templates/partials/navbar.html, 865 lines — markup 1–296, inline JS 298–389, inline CSS 391–866)

**Structure — desktop (lines 4–161):** fixed `header.main-header` > `nav.navbar` (60px tall, max-width 1400px, navbar.html:403–411):
- Brand (7–12): `Fav_icone.png` logo forced white via `filter: brightness(0) invert(1)` (navbar.html:424) + text "Collection Samathey".
- `ul.nav-menu` links, all inline Feather-style SVGs, **icon-only with `title=` tooltips only** (no visible labels, no aria-label): Accueil (icon+text, 17–25), Parcourir/`browse` (27–34), CP Animées/`animated_gallery` (36–49), Présentation (51–58), La Galerie/`decouvrir` — uses `gallerie_icone.png` img (60–64), La Poste (66–74), Contact (76–83).
- Account dropdown (85–160): button with `aria-expanded`/`aria-haspopup` (86), green online dot for authed users (91–93, styled 509–519), dark dropdown panel `#account-dropdown` (95–159) with avatar/username/category header, Mon Profil, staff-only Tableau de bord + `/admin/`, Déconnexion; anonymous: Se connecter / S'inscrire.

**Structure — mobile (163–296):** `.nav-mobile` (account btn + 3-span burger with `aria-label`/`aria-expanded`, 174–178), slide-in right panel `#mobile-menu-panel` (184–294) repeating all links + auth section, plus click-to-close `#mobile-menu-overlay` div (296) with inline `onclick`.

**Inline JS (298–389):** module-global `accountDropdownOpen`/`mobileMenuOpen`; `toggleAccountDropdown` (302–320), `toggleMobileMenu` (322–340, sets `body.overflow=hidden`), `closeMobileMenu` (342–353), `closeAccountDropdown` (355–362); outside-click close (364–375); Escape close (377–382); auto-close on resize >900px (384–388). All wired via inline `onclick=` attributes (86, 165, 174, 296). **No focus trap, no `inert`/`aria-hidden` management, no focus restoration.**

**Inline CSS (391–866, ~475 lines):** header gradient `rgba(181,96,11,.98)→rgba(160,80,8,.98)` + `backdrop-filter: blur(12px)` (398–399); hover states; dropdown dark theme `#1f1f1f→#151515` (531); mobile panel `#1a1a1a→#0d0d0d` (704). **Breakpoints: 900px (desktop menu → burger, 837–845) and 480px (smaller brand, full-width panel, 847–865).** All of this lives in the partial — re-parsed/re-sent inline on every page load, uncacheable.

**Template bug — `page_title` block is dead:** navbar.html:10 declares `{% block page_title %}Collection Samathey{% endblock %}` *inside an included template*. Django `{% include %}` does not participate in block inheritance, so the 14 per-page overrides (browse.html:5, contact.html:5, la_poste.html:5, profile.html:5, login.html:5, presentation.html:5, animated_gallery.html:5, gallery.html:8, decouvrir.html:5, register.html:103, verify_email.html:4, set_password.html:4, registration_complete.html:4, admin_dashboard.html:5, home.html:6) are **silently ignored** — the navbar brand always reads "Collection Samathey".

**Note:** pages must compensate for the fixed 60px header themselves (base.css sets no body padding-top); each page's inline CSS handles this ad hoc.

## 3. Postcard modal

- **templates/partials/postcard_modal.html is a 0-byte empty file, `{% include %}`d nowhere** (grep `postcard_modal` → no matches). Dead file.
- The real postcard viewer lives **inline in templates/browse.html**:
  - Detail popup markup: `#popup-overlay` (browse.html:477), `#popup-detail` (479–538) — close btn (480), flip-to-verso btn `#popup-flip` (486–493), prev/next arrows (495–499, 528–532), `#popup-image` (502), image-overlay actions: like w/ count (506–511), "Envoyer cette carte" link to `/la-poste/?postcard=<id>` (513–518), conditional "Voir l'animation" link to `/cp-animes/?highlight=<id>` (520–524), title+number footer (534–537).
  - Zoom modal: `#zoom-modal` (541–589) — backdrop, pan/zoom wrapper `#zoom-image-wrapper` (550–552), toolbar with zoom out/in, % level, reset, fit-to-screen (554–583), instructions strip with a literal 🖱️ emoji (585–587).
  - JS behavior (inline script from browse.html:594): `showDetail(id)` (2314–2353) reads from client-side arrays `filteredPostcards`/`allPostcardsData` (no fetch), sets `grande_url || vignette_url`, toggles `.active` classes, locks body scroll; `closeDetailPopup` (2355–2360); `togglePostcardSide` (2362–2378) swaps `dos_url`/front; prev/next + `updatePopup` (2380–2420); `updateNavButtons` (2422–2425); likes via `POST /api/postcard/<id>/like/` with CSRF header (2430–2465); zoom system `showZoom`/`closeZoomPopup`/wheel/drag/double-tap/pinch/keyboard handlers (1838–2087).
  - **Accessibility: no `role="dialog"`, no `aria-modal`, no focus trap, no focus restoration; buttons rely on `title` tooltips.**
- `templates/animated_gallery.html` has a *second, separate* modal implementation (`#animatedModal`, animated_gallery.html:156–223; JS 470–635) for videos, plus a success modal (226–236). So the site has ≥2 divergent modal systems, both inline.

## 4. base.css (static/css/base.css, 319 lines)

- **Reset (3–8):** `* { margin:0; padding:0; box-sizing:border-box; font-family:"Bookman Old Style", Georgia, serif; }` — font on the universal selector, so **every element (inputs, buttons) inherits the serif stack**; overriding requires `font-family: inherit` hacks (found at navbar.html:506, browse.html:3301, profile.html:2638, animated_gallery.html:1432, admin_dashboard.css ×7).
- **Body (10–17):** `background: #1a1208` (very dark brown), `color: white`, flex column min-height 100vh, `overflow-x: hidden`.
- **Animation library (19–184):** keyframes fadeIn/fadeInUp/Down/Left/Right, scaleIn, slideUp, float, pulseGlow, shimmer + utility classes `.animate-*` and `.delay-1..6` (169–174). **Trap at 177–179:** `[class*="animate-"] { opacity: 0 }` — anything matching substring `animate-` starts invisible and only appears if an animation runs to completion; no `prefers-reduced-motion` handling anywhere in the project (grep → 0 matches).
- **Messages (189–219):** fixed toast top-right (top 80px), `.alert-success` #28a745, `.alert-error` #dc3545, `.alert-info` #b5600b — Bootstrap-ish greens/reds clashing with the antique theme.
- **Footer (224–232):** orange gradient `#b5600b→#8b4513`, 12px text.
- **Buttons (237–258):** `.btn` pill (border-radius 25px) with orange gradient `#b5600b→#d1872c` and glow shadow + translateY hover.
- **Forms (263–284):** global styling for text/email/password/textarea; 2px orange-tint borders, radius 12px, glow focus (no `:focus-visible` outline strategy).
- **Scrollbar (289–304):** WebKit-only orange gradient scrollbar. **Selection (309–312):** orange.
- **Anti-copy (314–320):** `user-select: none` on body for all engines — **text is unselectable site-wide**; combined with main.js:4 right-click block.
- **No CSS variables, no design tokens, no media queries, no light theme, no print styles, no typography scale.** Global CSS is 319 lines; the actual page styling lives in giant inline `<style>` blocks in every template (16 templates: e.g. browse.html:2674+, la_poste.html:1314+, profile.html:1652+, animated_gallery.html:814+, navbar.html:391+).

## 5. static/js/ inventory (3 files)

| File | Lines | Loaded by | Status |
|---|---|---|---|
| `main.js` | 133 | base.html:40 (all pages extending base) + orphan admin_sync_ovh.html:40 | Loaded, but ~70% dead (below) |
| `browse.js` | 284 | **nothing** | Fully dead |
| `gallery.js` | 0 | **nothing** | Empty + dead |

**main.js details:**
- :4 — disables right-click site-wide (`contextmenu` preventDefault).
- :7–47 — "water particles" generator injecting `.water-particles`/`.particle-{small,medium,large}` divs on URLs containing `parcourir|browse|contact` (:50–54). **The CSS for these classes exists only in never-loaded files** (browse.css:91,133; contact.css:10), so it spawns 50 unstyled invisible divs + timers — pure waste.
- :57–64 — auto-hide `.alert` after 5s using animation `slideOut` which is **defined nowhere** (grep `@keyframes slideOut` → 0); the element is still removed by the setTimeout, so toasts vanish without animating.
- :68–102 — `loginSubPopup()`/`burgerMenuToggle()` target `#conn_wrapper`, `#menu_wrapper`, `#triangle`, `#triangle_1` — IDs from a previous navbar that **no longer exist in any template**; dead.
- :105–134 — outside-click closer for those same ghost elements; dead.

**browse.js details (all dead):** fetch-based `showDetail` hitting `/api/postcard/<id>/` (:50–76), front/back toggle (:79–88), `showZoom` w/ member gate `popup_non_membre` (:91–123), mouse-follow zoom (:126–147), arrow nav (:150–183), `cinemaMode` slideshow (:186–210), close-all + keyboard nav (:213–285). Targets `#popup_detail`/`#popup_zoom`/`#fade` etc. — **those IDs exist in no template** (grep → 0). browse.html reimplemented all of this inline with different IDs (`popup-detail` vs `popup_detail`).

**Actual JS reality:** every page's behavior is inline `<script>` in its template (browse.html:594, home.html:105, contact.html:515, la_poste.html:721, decouvrir.html:62, gallery.html:75, animated_gallery.html:239, profile.html:992, admin_dashboard.html:1264, intro.html:204, navbar.html:298, etc.).

**External scripts:** GA gtag (base.html:13 → every page), Chart.js from jsDelivr CDN (admin_dashboard.html:1262), YouTube iframe API (decouvrir.html:60).

## 6. Orphan CSS files (static/css/)

Loaded: `base.css` (base.html:8), `gallery.css` (gallery.html:5 via extra_css), `admin_dashboard.css` (admin_dashboard.html:1977 — linked at the **bottom of the template body**, not in the head block, causing FOUC).
**Never referenced anywhere:** `browse.css` (482 ln), `contact.css` (250 ln), `home.css` (115 ln), `presentation.css` (195 ln) — grep `css/(browse|contact|home|presentation)\.css` → 0 matches. contact.css:94 references a font "Eskapade" that is never loaded.

## 7. Fonts

- Site-wide stack: `"Bookman Old Style", Georgia, serif` (base.css:7; repeated intro.html:19). Bookman Old Style is a Windows system font — macOS/Android/Linux users get Georgia. **No webfonts at all**: zero `@font-face`, zero Google Fonts/Typekit/CDN font links in the project (grep → 0 matches).
- `'Dancing Script', cursive` is used for handwriting effects at la_poste.html:2308, 2782, 2817 and contact.html:211 **but the font is never loaded** — it silently falls back to the generic `cursive` (Comic Sans MS on Windows). Undermines the whole "handwritten postcard" effect.
- Emails use Georgia/Courier New (templates/emails/verification_code.html:8,42; core/views.py:196,267).

## 8. Color palette actually in use (hex frequency across templates + static/css)

Core brand: `#b5600b` burnt orange/ochre ×240 (primary — nav, buttons, borders, glows), `#d1872c` light ochre ×74 (gradient partner), `#ffc168` gold accent ×63, `#8b4513` saddle brown (footer/scrollbar), `#1a1208` near-black brown body bg ×44, `#2d1f0d` ×22, `#0d0906` ×10, plus neutral darks `#1f1f1f/#151515/#1a1a1a/#0d0d0d/#202020/#252525`. Utility colors imported from Tailwind's palette: greens `#4ade80/#22c55e/#16a34a/#10b981`, reds `#f87171/#fca5a5/#ef4444/#dc2626/#ff6b6b`, ambers `#f59e0b/#fbbf24/#ffd700`, blues `#3b82f6/#60a5fa`, Bootstrap `#28a745/#dc3545/#ffc107`, cream `#f5f0e8` (emails only). No tokens/variables — all hardcoded per file; the "same" orange appears as rgba(181,96,11,x) at dozens of opacities.

## 9. Brand assets (names only)

**static/images/**: Carte_Membre.jpg, Carte_Membre_bis.jpg, Carte_Membre_ter.jpg, Carte_postale.png, Connect_Icone.png, Cpa_Vierge.jpg, Fav_icone.png, Loupe_icone.png, Samathey.png, Samathey_blanc.png, Timbre_10c.png, Timbre_5c.png, Verso.png, burger_icon.png, burger_icon.svg, cinema.png, clape-cine.jpg, close_icon.jpg, close_icon.png, cp_bg_présentation.jpg (non-ASCII filename — risky for manifest storage/CDN), cp_contact.png, cp_contact_1.png.jpg (double extension), fleche-laterale.png, fleche-laterale-1.png, gallerie_icone.png, oeil.png, oeil_icone.png, placeholder.jpg; subfolder **decouvrir/**: Cadre_1..6_Clic.png + Cadre_1..6_Off.png (12 frame images).
**static/video/**: Annimate_CPA_optimized.mp4 (referenced only as fallback at home.html:114).

## 10. Accessibility summary

- Icon-only nav links have `title` but no `aria-label`/visible text (navbar.html:28–83); `title` is unreliable for screen readers and useless on touch.
- No skip-to-content link, no `sr-only` utility, no `aria-live` regions, no `:focus-visible` styles anywhere (greps → 0).
- Modals (browse.html:479, 541; animated_gallery.html:156) lack `role="dialog"`, `aria-modal`, focus management.
- `user-select:none` (base.css:315–319) + right-click block (main.js:4) break copy, and harm assistive tech.
- Content starting at `opacity:0` pending animations (base.css:177–179) with no `prefers-reduced-motion` fallback.
- Alerts auto-dismiss in 5s (main.js:60–63) with no pause/dismiss control.
- Logo `alt="Logo"` (navbar.html:9); emoji-in-text instructions (browse.html:586).
- Inline `onclick=` handlers throughout; overlay close divs are non-focusable.

## 11. Responsiveness approach

No global strategy: base.css has **zero media queries**; navbar handles 900px/480px (navbar.html:837–865); every page template rolls its own breakpoints inside its inline `<style>`. Fixed header height 60px is compensated per-page. Toast container `max-width:400px` fixed right (base.css:189–195).

## 12. Migration-relevant notes (static side)

Static served by WhiteNoise with `CompressedManifestStaticFilesStorage` (le_postier/settings.py:35,100–103) — hashed filenames mean the non-ASCII `cp_bg_présentation.jpg` and stray dupes (`close_icon.jpg`+`.png`, `burger_icon.png`+`.svg`, `fleche-laterale` twins, `cp_contact_1.png.jpg`) should be normalized before the OVH move. The orphan `admin_sync_ovh.html` name suggests an OVH sync UI was planned but the template is just a copy of base.html.


## Issues (flat list)

- Dead partial: templates/partials/postcard_modal.html is 0 bytes and included nowhere; the real modal is duplicated inline in browse.html:477-592 and a second modal system exists in animated_gallery.html:156-236
- Dead JS: static/js/browse.js (284 lines) is loaded by no template and targets IDs (#popup_detail, #fade, #popup_zoom) that exist in no template; static/js/gallery.js is empty and unloaded
- main.js is ~70% dead: particle system (main.js:7-54) injects divs whose CSS lives only in never-loaded browse.css/contact.css (invisible DOM churn); legacy nav functions (main.js:68-134) target ghost IDs #conn_wrapper/#menu_wrapper; alert hide references undefined @keyframes slideOut (main.js:61)
- Orphan CSS: static/css/browse.css, contact.css, home.css, presentation.css are referenced by zero templates; admin_dashboard.css is linked at the bottom of the body (admin_dashboard.html:1977) causing FOUC
- Template bug: {% block page_title %} lives inside the included navbar (navbar.html:10) so all 15 per-page overrides (e.g. browse.html:5, contact.html:5) are silently ignored - navbar text never changes
- Every page shares the same <title> 'Collection Samathey' (base.html:10; only home.html:5 overrides it with identical text); no meta description, OG tags, or canonical anywhere - severe SEO gap
- Google Analytics loads unconditionally with no consent mechanism (base.html:13-19) - GDPR/CNIL non-compliance for a French site; also duplicated in orphan admin_sync_ovh.html:13-19
- admin_sync_ovh.html is an exact byte-for-byte copy of base.html referenced by no view - orphan duplicate layout
- 'Dancing Script' font is used for handwriting effects (la_poste.html:2308,2782,2817; contact.html:211) but never loaded (no @font-face/Google Fonts in project) - falls back to Comic Sans-class 'cursive'; site font 'Bookman Old Style' (base.css:7) only exists on Windows
- Font stack applied via universal selector * (base.css:3-8), forcing font-family:inherit workarounds in at least 11 places (navbar.html:506, browse.html:3301, profile.html:2638, admin_dashboard.css x7)
- No design tokens: ~30 hardcoded hex colors including Tailwind/Bootstrap defaults (#4ade80, #3b82f6, #28a745, #dc3545) mixed with the antique ochre palette (#b5600b x240 occurrences); rgba(181,96,11,*) repeated at dozens of opacities across 16 inline <style> blocks
- All page CSS/JS is inline in templates (16 templates with <style> blocks, 15+ with <script> blocks; navbar alone carries 475 lines CSS + 92 lines JS inline at navbar.html:298-866) - uncacheable, unminified, duplicated
- Anti-copy measures: user-select:none on body (base.css:315-319) plus site-wide contextmenu block (main.js:4) - breaks text selection/copy for legitimate users and assistive tech
- Accessibility: no skip link, no aria-live on toasts (base.html:25), no :focus-visible styles, no prefers-reduced-motion (base.css animations start content at opacity:0 via [class*='animate-'] at base.css:177-179), modals lack role=dialog/aria-modal/focus traps, icon-only nav links rely solely on title attributes (navbar.html:28-83), logo alt='Logo' (navbar.html:9)
- Two divergent breakpoint systems: navbar breaks at 900px/480px (navbar.html:837-865) while base.css has zero media queries and each page invents its own; fixed 60px header offset is compensated ad hoc per page
- Footer is a single unstyled credit line '- A Z DATA Production 2025 -' (base.html:37) - no navigation, contact, or legally required mentions legales
- Static asset hygiene problems for the OVH/WhiteNoise manifest pipeline (settings.py:103): non-ASCII filename cp_bg_présentation.jpg, double-extension cp_contact_1.png.jpg, duplicate variants (close_icon.jpg/.png, burger_icon.png/.svg, fleche-laterale/-1.png)
- Toast palette (#28a745 green / #dc3545 red at base.css:206-219) and dropdown status greens (#4ade80/#22c55e navbar.html:515) clash with the museum/antique brand direction
- External CDN dependencies scattered per-page: Chart.js via jsDelivr (admin_dashboard.html:1262), YouTube iframe API (decouvrir.html:60), GA gtag (base.html:13) - no local bundling strategy
- intro.html bypasses base.html entirely (standalone document, core/views.py:1202) duplicating font stack and palette


## Quick wins

- Delete dead files: static/js/browse.js, static/js/gallery.js, static/css/browse.css, contact.css, home.css, presentation.css, templates/partials/postcard_modal.html, templates/admin_sync_ovh.html - zero runtime impact, removes ~1,500 lines of misleading code
- Strip main.js to its two live behaviors (contextmenu block + alert auto-hide) or remove entirely; also drop the particle generator that renders nothing
- Fix the page_title mechanism: replace {% block page_title %} inside the navbar include with a context variable or move the block into base.html - instantly activates the 15 existing per-page titles; do the same for <title> to give every page a unique title tag
- Load Dancing Script (or a licensed script alternative) via @font-face with a self-hosted woff2 - the handwriting features on La Poste and Contact immediately render as designed
- Introduce CSS custom properties in base.css (:root tokens for the ochre scale, darks, success/error) and replace the Tailwind/Bootstrap stray colors - mechanical find-replace with the frequency table in this report as the mapping
- Move navbar's 475-line <style> and 92-line <script> into base.css/main.js (or navbar.css/nav.js) so they cache; same pattern later for each page's inline blocks
- Add basics to base.html head: meta description block, og:title/og:image (Samathey.png is a ready-made brand asset), theme-color #1a1208, correct favicon type, preload of the woff2 font
- Remove user-select:none and the contextmenu blocker (protection is illusory - images remain downloadable via devtools/URL) or scope protection to gallery images only
- Add prefers-reduced-motion media query disabling the .animate-* system and a :focus-visible outline style in base.css - two small blocks, large a11y gain
- Rename problem static files before the OVH migration: cp_bg_présentation.jpg to ASCII, delete cp_contact_1.png.jpg double extension and duplicate icon variants
- Add role='alert' aria-live='polite' to #messages-container in base.html:25 and role='dialog' aria-modal='true' to the browse and animated-gallery modals - one-line changes each
- Replace footer line with a minimal three-column footer (collection blurb, nav links, mentions legales/contact) - single shared template edit