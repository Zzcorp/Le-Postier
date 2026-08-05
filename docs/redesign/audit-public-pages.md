# Audit — Public Content Pages, "Le Postier" (Collection Samathey)

Scope: `templates/home.html`, `templates/intro.html`, `templates/presentation.html`, `templates/decouvrir.html`, `templates/contact.html` + their (nominally) paired CSS files, plus the shared chrome they inherit (`templates/base.html`, `templates/partials/navbar.html`, `static/css/base.css`). All paths below are relative to `C:/Users/mathe/Documents/CODING/Empire/le-postier/`.

---

## 0. Shared foundation (affects every audited page)

### 0.1 How pages are assembled
- `templates/base.html:8` loads exactly one stylesheet: `static/css/base.css`. An `{% block extra_css %}` hook exists at `base.html:9` but **none of the five audited templates use it** — every page instead ships a large inline `<style>` block inside `{% block content %}`.
- **All three "paired" CSS files are dead code.** A project-wide grep for `home.css|presentation.css|contact.css` returns zero references. They are legacy files from a previous markup generation:
  - `static/css/home.css` (116 lines) targets `#bg_cp_video`, `#welcome_bg`, `.welcome_title`, `.browse-button` — none of these selectors exist in the current `home.html`.
  - `static/css/contact.css` (251 lines) targets `#page_content`, `#contact_text`, `#timbre_1_colle`, `#cp_contact` — none exist in current `contact.html`. It also references a never-loaded font `"Eskapade"` (`contact.css:94`).
  - `static/css/presentation.css` (196 lines) is dead too, but **dangerously so**: it re-declares class names that ARE used by the current inline styles (`.presentation-container` at `presentation.css:2` vs `presentation.html:207`; `.presentation-header` 8 vs 215; `.presentation-title` 25 vs 224; `.presentation-date` 32 vs 231; `.highlight-box` 112 vs 299; `.timeline` 127 vs 324; `.timeline-item` 144 vs 336; `.discover-btn` 174 vs 377) with different values (e.g. `font-size: 3em` vs `clamp(2.2rem,5vw,3.5rem)`). If an implementer "reconnects" this file during the overhaul without noticing, styles will silently conflict. Recommend deleting all three or rebuilding them as the single source of truth.
- `base.html:13-19`: Google Analytics (G-YZX5PNSJZG) injected unconditionally with no consent banner — a GDPR/CNIL exposure for a French-audience site; relevant when re-hosting on OVH.
- `base.html` has **no meta description, no Open Graph/Twitter tags, no canonical URL** — poor sharing/SEO for a showcase site (sitemap exists at `core/views.py:41-70`, so SEO is otherwise cared about).
- Footer is a bare `<p>- A Z DATA Production 2025 -</p>` (`base.html:37`) styled as an orange gradient bar (`base.css:224-232`) — no sitemap links, no legal mentions (mentions légales are legally expected on a French site), no contact link.

### 0.2 Global CSS (`static/css/base.css`)
- `base.css:3-8`: universal selector `*` hard-forces `font-family: "Bookman Old Style", Georgia, serif` on every element. Consequences: (a) a single typeface for display, body, buttons and form fields — no typographic hierarchy is possible; (b) "Bookman Old Style" is a Windows system font — macOS/iOS/Android/Linux all silently fall back to Georgia, so most visitors see a different site than the designer; (c) no webfonts are loaded anywhere in the project. For a "museum-quality" overhaul this is the first thing to replace with a proper loaded pairing (e.g., a display serif + text serif) and CSS variables.
- `base.css:10-17`: body = `#1a1208` (near-black brown) + white text; dark theme is the site default, yet home.html's second section is cream/white (see §1), the only light-mode surface in the audited set.
- `base.css:177-179`: `[class*="animate-"] { opacity: 0; }` — every element carrying any `animate-*` class starts invisible and only becomes visible when its CSS animation runs. If animations are disabled (older browser, extension, future `prefers-reduced-motion` handling done naively) content is permanently invisible. There is **no `prefers-reduced-motion` support anywhere in the project**.
- `base.css:136-174` defines the animation utility classes at 0.5–0.7s durations, then `home.html:704-707`, `decouvrir.html:391-393` and `presentation.html:406-407` **redefine the same class names inline** at 0.8s — duplicate keyframes (`fadeIn`, `fadeInUp`, `fadeInDown`, `scaleIn`) exist in 4+ places with different timings; last-loaded wins.
- `base.css:314-320`: `user-select: none` on `body` (mis-commented "Disable right-click") — visitors cannot select/copy any text sitewide, including the contact instructions and presentation copy. Hostile for accessibility and screen-reader interaction models; provides zero real protection for images.
- `base.css:289-304`: custom orange-gradient scrollbar; `base.css:309-312`: orange selection color (moot given user-select none).
- Palette is scattered as raw hex throughout every file with no custom properties: `#b5600b` (ochre primary), `#d1872c` (amber), `#ffc168` (gold highlight), `#1a1208` / `#2d1f0d` (browns), `#f5f0e8` (cream), `#5a4a3a` / `#4a3728` (ink browns), plus off-brand strays: `#ffd700` gold particles (`intro.html:55,140`), `#ff0000`/`#cc0000` YouTube red (`decouvrir.html:350,359`), `#4ade80/#22c55e` green (`navbar.html:515`), `#f87171` red (`navbar.html:631`), grey `#666/#888` disabled gradient (`contact.html:411`). A token layer (CSS variables) is a prerequisite for the redesign.

### 0.3 Navbar (`templates/partials/navbar.html`, included by every audited page except intro)
- Fixed 60px header with an **opaque saturated orange gradient** (`navbar.html:392-401`) — the loudest element on every page; sits directly against the dark museum-ish page backgrounds. For an elegant overhaul this is the single highest-impact chrome change.
- ~475 lines of inline CSS (`navbar.html:391-866`) and ~91 lines of inline JS (`navbar.html:298-389`) shipped on every page load.
- Desktop nav is icon-only for 6 of 7 links (`nav-icon-only`, `navbar.html:28-83`) with only `title` tooltips — labels hidden, poor discoverability/accessibility; only "Accueil" keeps text (`navbar.html:18-24`).
- The brand slot reuses `{% block page_title %}` (`navbar.html:10`), so the logo text changes per page ("Présentation", "Contact", "La Galerie") instead of remaining a stable wordmark.

---

## 1. Home — `templates/home.html` (+ dead `static/css/home.css`)

**Purpose.** Landing page: cinematic hook (video hero) + welcome text + routing to the three main destinations. Served by `home()` at `core/views.py:1205-1227`; first visit per day is intercepted and redirected to `/intro/` (`views.py:1208-1209`, logic `should_show_intro` `views.py:1159-1177`).

**Layout structure.**
1. `header.hero-section` — 100vh flex-centered hero (`home.html:11-53`, CSS `home.html:402-408`):
   - `#video-poster` gradient placeholder shown instantly (`home.html:14-16`, CSS 417-437, animated `gradientPulse`).
   - `<video autoplay muted loop playsinline preload="none">` with empty `src` filled by JS (`home.html:18-20`).
   - `.video-overlay` vertical dark gradient (`home.html:447-458`) and `.video-transition` fade-to-black layer (`home.html:461-473`).
   - `.video-indicators` clickable dots, absolute at `bottom:100px` (`home.html:28`, CSS 476-506; max 10 dots created at JS `home.html:192`).
   - `.hero-content`: h1 + subtitle + pill CTA with arrow SVG (`home.html:30-43`).
   - `.scroll-indicator` "Découvrir" + bouncing arrow at `bottom:40px` (`home.html:45-52`, CSS 562-591).
2. `section.welcome-section` — cream/white section (`home.html:56-102`, CSS 594-597 gradient `#f5f0e8→#fff→#f5f0e8`): deco lines + "1873 - 1914" (`home.html:58-62`), h2, two justified paragraphs, italic signature line, and a 3-button action row (`home.html:79-100`): primary "Parcourir la collection", secondary outline "CP Animées", tertiary tinted "Présentation".

**Imagery used.** No stills at all — the hero streams randomized **animated postcard videos from MEDIA storage**: the view samples 30 random postcards (`order_by('?')`, `views.py:1212-1214` — expensive query) and collects up to 15 animated URLs; `Postcard.get_animated_urls()` (`core/models.py:268-297`) builds URLs like `{MEDIA_URL}animated_cp/{number}.mp4` by doing **filesystem `exists()` probes per extension per variant on every request** (up to ~80 stat calls per postcard). Fallback: `static/video/Annimate_CPA_optimized.mp4` (exists; referenced `home.html:114`). This is the page most directly coupled to the Render→OVH media migration: hero videos are served by the Django app from local media disk, no CDN, no poster frames, no HLS/adaptive delivery.

**Inline volume.** 733-line template: ~103 lines markup (1-103), ~292 lines JS (105-396, the `VideoCarousel` class), ~335 lines CSS (398-732). Nothing cacheable across pages.

**French copy (keep).** « Embarquez pour la belle époque ! » (h1, `home.html:32`); "La navigation fluviale en cartes postales anciennes" (subtitle, 35); "Parcourir la collection" (CTA, 38); "Découvrir" (scroll cue, 46); "1873 - 1914" (60); "Bienvenue dans notre collection" (64); body copy about strolling the banks at the « Belle Époque », "période (1873-1914) pleine d'insouciance et d'optimisme" (66-70) and "des métiers et des bateaux aujourd'hui disparus… boucles de la Seine" (72-75); "Bonne visite à tous !" (77); buttons "Parcourir la collection" / "CP Animées" / "Présentation" (85/91/98).

**Interactions.** `VideoCarousel` (`home.html:116-388`): shuffles videos (182-187), caps at 50 (144 — moot, view sends ≤15), creates ≤10 dot indicators (189-203), fade-to-black between clips (279-313), min display 6s / cap 20s / load timeout 8s (130-132, 294-299), removes failing videos from rotation (315-331, 361-380), and works around mobile autoplay policy by waiting for first click/touch/scroll (167-180). Initialized 100ms after DOMContentLoaded (391-395).

**Design weaknesses.**
- *Typography*: h1 at `font-weight:600` with a blurry `2px 2px 30px` shadow (`home.html:517-523`); decorative guillemets baked into the headline text; no display face. Welcome paragraphs `text-align: justify` (`home.html:637`) produce rivers at mobile widths. The 768px media query (`home.html:721`) hard-sets `hero-title` to 1.8rem, defeating the existing fluid `clamp()`.
- *Hierarchy*: two competing CTAs to the same destination (hero CTA `home.html:37` and welcome primary button 80); three welcome buttons in three different styles (670-701) diluting the primary action.
- *Color*: saturated orange gradient pills with heavy colored glows (`home.html:538-551`, 670-679) read as consumer-app, not museum; the cream welcome section is the only light surface in the whole site — jarring against dark nav/footer and every other page.
- *Motion*: bouncy hovers (`translateY(-5px) scale(1.05)`, 548-551), bouncing scroll arrow (588-591), pulsing poster; content hidden until animations fire (708); no reduced-motion path; carousel's fade-to-black every 6-20s is restless for a "contemplative" brief.
- *Engineering*: 15+ `console.log` calls left in production JS (146, 217, 222, 243, 258, 266, 272, 276, 285, 296, 316, 339, 363…); duplicated keyframes vs base.css; dot indicators have English `aria-label="Video N"` (197) on a French site; the video element has no accessible name/track.

---

## 2. Intro splash — `templates/intro.html` (standalone, no base.html)

**Purpose.** A once-per-day, 3-second fake "loading" splash. `intro()` (`core/views.py:1198-1202`) marks it seen (per user or session via `IntroSeen`) and renders with `redirect_url` from `?next=`; `home()` redirects here on first visit of the day (`views.py:1208-1209`).

**Layout/sections.** Full-viewport centered column: 3 drifting gradient "waves" (`intro.html:171-175`, CSS 29-49), 40 JS-spawned gold particles (206-217, CSS 51-66), pulsing orange rounded-square logo containing a hand-drawn white fish SVG (180-192), h1 "Le Postier" with glow animation (193), shimmer progress bar + % counter + rotating status text (194-201).

**Imagery.** None — all decoration is CSS/SVG. The fish logo is inline SVG (181-191); its style (flat clip-art fish in a glowing orange app-icon square) is the single least "museum" asset in the audited set.

**Inline volume.** 251-line file: ~161 lines CSS (8-168), ~46 lines JS (204-249). Self-contained; does not load base.css — and its background is `#1a1a1a→#202020` grey (11-12), not the site's `#1a1208` brown, so the splash doesn't even match the brand it introduces.

**French copy (keep).** Title "Le Postier - Chargement" (7); "Le Postier" (193); "Chargement de la collection..." (198); fake status strings (224-230): "Connexion au serveur...", "Chargement des cartes postales...", "Préparation de la collection...", "Mise en place de l'interface...", "Finalisation...".

**Interactions.** None available to the user: progress is simulated on a 100ms timer to reach 100% in ~3s (232-243), then hard redirect `window.location.href = '{{ redirect_url }}'` at exactly 3000ms (246-248). **No skip button, no click-through, no reduced-motion, no way out.**

**Design weaknesses.** (a) It fabricates a 3-second delay for every visitor once per day — an anti-pattern that directly costs bounce rate on the most important entry path; the "loading" messages are fictional. (b) Aesthetic (glow, shimmer, gold particles, pulsing app icon) is arcade-like, opposite of the high-end brief. (c) `redirect_url` comes from the `next` GET param and is written into a JS navigation (247) — Django autoescaping prevents HTML injection but not open-redirect abuse (`/intro/?next=https://evil.example`); should be validated with `url_has_allowed_host_and_scheme`. (d) If the overhaul keeps any intro at all, a sub-second brand mark reveal with an immediate skip would fit better; the daily-repeat logic (`views.py:1159-1177`) deserves reconsideration too.

---

## 3. Présentation — `templates/presentation.html` (+ dead/conflicting `static/css/presentation.css`)

**Purpose.** Editorial "about" page for the collection. View is a bare render (`core/views.py:1354-1356`).

**Layout structure.** Dark page (`#1a1208`, fixed gradient + faint radial pattern backdrop, `presentation.html:10-12`, CSS 183-204), 1000px container:
1. Header (16-25): layered-stack SVG ornament, h1 "Présentation", italic "1873 - 1914", gradient underline bar.
2. Three cards in a responsive grid — 1-col mobile, 3-col ≥768px (`presentation.html:247-252`, 413-421): "La Navigation Fluviale" (30-48, barge SVG icon), "Notre Collection" (51-70, fish+gold-star SVG — the original logo motif), "Un Patrimoine Préservé" (73-98, steamboat SVG). Dark gradient cards, 20px radius, hover lift + orange border/glow (254-266).
3. Quote highlight box with orange left border + faded quote glyph (102-110, CSS 299-321).
4. "Chronologie" timeline, 4 items — 1873, 1889, 1900, 1914 (113-167), left-border rail with glowing dot markers (336-369).
5. CTA "Parcourir la collection" pill (170-178, CSS 377-403).

**Imagery.** **Zero photographs or postcards.** The presentation page of a postcard museum shows only hand-drawn inline SVG line icons. This is the page's biggest missed opportunity: it should carry hero scans of star cards, dated postmarks, handwriting details. (An unused asset `static/images/cp_bg_présentation.jpg` exists — note the accented filename, risky for URL encoding — suggesting a background image was once intended.)

**Inline volume.** 464-line template: ~180 lines markup, ~282 lines CSS (182-463), no JS. Animation stagger is done via inline `style="animation-delay: …"` attributes (51, 73, 102, 113, 170).

**French copy (keep).** Card 1: "La période de la Belle Époque a vu l'apogée de la navigation fluviale en France…" (44-47). Card 2: "près de 2000 cartes postales anciennes numérisées et cataloguées… Chaque carte raconte une histoire…" (66-69). Card 3: "témoignage précieux de notre patrimoine fluvial… métiers disparus… bateaux aujourd'hui oubliés" (94-97). Quote: "…préserver notre mémoire collective et de transmettre aux générations futures la richesse de notre patrimoine fluvial." (107-109). Timeline entries: 1873 début/navigation à vapeur (124-126), 1889 Exposition Universelle (136-139), 1900 apogée + démocratisation de la correspondance (149-152), 1914 fin de la Belle Époque (162-165).

**Interactions.** Card hover lift/glow (262-266), button hover (392-403); entrance fades. Nothing else — fully static.

**Design weaknesses.**
- *Hierarchy/layout*: at ≥768px the three cards compress long justified paragraphs (`text-align: justify`, 296) into ~300px columns — dense, hard to read; an editorial page wants a single measured column (~65ch) with generous leading, not a card grid.
- *Typography*: same single-font problem; card titles in flat orange `#b5600b` (284-289) on dark brown have mediocre contrast; timeline dates in `#ffc168`.
- *Color/motion*: glow-on-hover cards, glowing timeline dots (`drop-shadow`, 354-356), gradient pill CTA — the same app-like vocabulary as home.
- *Duplication risk*: dead `presentation.css` re-declares live class names (see §0.1) — must be deleted or merged during the overhaul.
- The timeline is a strong content asset presented weakly (plain circles, no imagery, no era illustration); prime candidate for a redesigned horizontal frieze with card scans per period.

---

## 4. La Galerie — `templates/decouvrir.html`

**Purpose.** Showcase of 6 "animated paintings": framed postcard images that reveal an alternate frame on hover and open a YouTube animation in a modal on click. Data is hardcoded in `decouvrir()` at `core/views.py:1359-1399`.

**Layout structure.** Dark gradient page (126-129); centered header "La Galerie" + subtitle (10-13, CSS 132-148); `.paintings-grid` 3-col → 2-col (≤1024px) → 1-col (≤600px) (156-160, 364-388); each item = frame with two stacked `<img>` (off/on) + hover info bar (24-36); fullscreen modal with backdrop, close button, title, 16:9 YouTube player (43-56).

**Imagery.** 12 static PNGs, all present on disk: `static/images/decouvrir/Cadre_{1..6}_Off.png` + `Cadre_{1..6}_Clic.png`, referenced via hardcoded `/static/...` paths in the view (`views.py:1364-1396` — bypasses `{% static %}`/hashed storage, will break if `STATIC_URL` changes on OVH or if ManifestStaticFilesStorage is adopted). Videos are **YouTube embeds** via the IFrame API (external `<script src="https://www.youtube.com/iframe_api">`, `decouvrir.html:60`).

**Inline volume.** 400-line template: ~57 lines markup, ~62 lines JS (62-123), ~275 lines CSS (125-399), + external YouTube script.

**French copy (keep).** "La Galerie" (11), "Découvrez quelques tableaux animés" (12), "Voir la vidéo" (34), modal error fallback "Impossible de charger la vidéo ici." / "Regarder sur YouTube" (99-102). Painting titles (from `views.py:1363-1397`): "Ascenseur de la Terrasse", "Accident de l'archevêché", "Bateau « Touriste »", "Machine de Marly", "Yacht « Le Druide »", "La Pénichienne".

**Interactions.** Hover: lift `translateY(-15px) scale(1.02)` (168-171), off→on image crossfade (202-208), info bar slides up (225-228) with pulsing play icon (245-252). Click anywhere on item (inline `onclick`, 22) opens modal, locks body scroll, creates/reuses a `YT.Player` with autoplay (71-109); close via backdrop / X / Escape (44-46, 111-122); on YT error a red "Regarder sur YouTube" link replaces the player (94-105).

**Design weaknesses.**
- **Placeholder rickroll in production:** painting 2 "Accident de l'archevêché" uses `video_id: 'dQw4w9WgXcQ'` (`core/views.py:1372`) — Rick Astley's "Never Gonna Give You Up". Clearly a leftover placeholder; must be replaced with the real animation ID.
- *Touch/keyboard*: titles and the "Voir la vidéo" affordance exist only on hover (219-228) — touch users see unlabeled frames until they tap; items are `div onclick` with no `tabindex`/`role="button"`/keyboard handler — completely inaccessible via keyboard; the modal has no focus trap and no `aria-modal`.
- *Performance/CLS*: both off and on images load eagerly for all 6 items (no `loading="lazy"`, no `width/height` attributes → layout shift); hover preloading is fine but doubling payload up front is not.
- *Third-party dependence*: full YouTube (not `youtube-nocookie.com`), tracking cookies without consent (GDPR, cf. §0.1), and the fallback button in YouTube brand red (`#ff0000`, 347-361) breaks the palette. For the OVH move with self-hosted media, these six animations are prime candidates for self-hosted `<video>` (the files may already exist under `media/animated_cp/`).
- *Naming*: page/nav label is "La Galerie" but URL/view/template are `decouvrir` (`views.py:48` sitemap `/decouvrir/`), and the site has ANOTHER gallery ("CP Animées", `animated_gallery`) — information architecture confusion worth resolving in the overhaul.
- Modal close button positioned at `top:-15px; right:-15px` outside the panel (286-302) — can clip against viewport edges on small screens.

---

## 5. Contact — `templates/contact.html` (+ dead `static/css/contact.css`)

**Purpose.** Contact form staged as writing a real ancient postcard: type the message on a blank CPA scan, affix a stamp, apply the recipient signature, then "post" it. Backed by `contact()` (`core/views.py:1402-1428`) → saves `ContactMessage`, emails admins.

**Layout structure.** Dark fixed-gradient background + 15 floating gold particles (10-12, JS 570-610); 800px container: header (15-18); postcard: `static/images/Cpa_Vierge.jpg` (exists) with an absolutely-overlaid form in a 55%/45% grid (21-57, CSS 195-202) — message `<textarea>` left, dashed stamp slot top-right (41-46), dashed recipient/signature line right (48-54); italic instruction line (60-63); interactive tray (65-99) in a blurred glass bar: 2 stamps + signature + submit; conditional success overlay (101-107).

**Imagery.** All present in `static/images/`: `Cpa_Vierge.jpg` (postcard), `Timbre_5c.png`, `Timbre_10c.png` (stamps), `Samathey_blanc.png` (tray version) → `Samathey.png` applied on card. The postcard-as-form concept is genuinely charming and on-brand — worth keeping and refining in the redesign.

**Inline volume.** 612-line template: ~109 lines markup, ~403 lines CSS (111-513), ~97 lines JS (515-611). The particle system even injects a `<style>` element at runtime (591-609).

**French copy (keep).** "Nous Contacter" (16); "Envoyez-nous un message sur notre carte postale" (17); placeholders "Écrivez votre message ici..." (35), "Cliquez sur un timbre" (43), "Cliquez sur la signature" (52); instruction "Veuillez affranchir au tarif en vigueur de 10 centimes puis inscrivez le nom du destinataire" (61-62); button "Poster la carte" (94); success "Carte envoyée avec succès !" / "Votre message a bien été transmis." (104-106).

**Interactions.** Stamp click applies image to card with a slam animation (`stampApply`, 274-286; JS `selectStamp` 519-536); signature click applies with a write-in clip-path reveal (`signatureApply` 329-340; JS 538-551); submit unlocks only when message non-empty AND the **10c** stamp AND signature are applied (`checkFormReady` 553-564; the 5c stamp sets `stampApplied=false` at 533); ready state pulses (`pulseGlow` 434-441). Postcard tilts in 3D on hover (181-187). Message preserved on re-render via `{{ form.message.value|default:'' }}` (38).

**Design weaknesses.**
- **Silent-failure trap:** choosing the 5c stamp visually applies it to the card exactly like the 10c one, but the submit button just stays grey forever with no message. The riddle ("affranchir au tarif en vigueur de 10 centimes") is cute, but there is zero feedback path — no shake, no hint, no `aria-live` — and the instruction sits *below* the fold of the card. Most costly UX defect on the page.
- **No reply channel:** `ContactForm` exposes only `message` (`core/forms.py:9-20`); anonymous visitors provide no email/name, and the admin notification only includes IP (`views.py:236-259`) — the owner literally cannot answer non-logged-in correspondents. The redesigned card should add a sender line (thematically: "expéditeur").
- *Layout fragility:* the textarea is positioned with confessed hacks — `margin-top: 38%; height: calc(100% - 38%)` with comments "ADJUSTED: moved up by 200px" / "KEY FIX" (`contact.html:30, 204-220`) — tightly coupled to `Cpa_Vierge.jpg`'s aspect ratio; any image swap breaks the writing area. Same for `.recipient-area`'s `margin-top:-30px; margin-left:50px` (298-299).
- *Typography:* the handwriting font `'Dancing Script'` (211) is **never loaded** (no webfont link anywhere) → falls back to generic `cursive`/Georgia, killing the manuscript illusion. (Dead `contact.css:94` references another never-loaded font, "Eskapade".)
- *Success state:* the overlay (101-107, CSS 444-456) is `position:fixed`, z-index 1000, with **no close button, no auto-dismiss, no backdrop click** — it permanently covers the page until reload; it also uses an ✉️ emoji as its icon (104). The form underneath is re-rendered empty but unreachable.
- *Accessibility:* textarea has no `<label>` (placeholder only); stamps/signature are `<img onclick>` — no keyboard access, no roles, no state announcement; disabled submit gives no reason; 500-char `maxlength` (37) with no counter.
- *Motion/decor:* floating particles + 3D tilt + pulse glow — again the glow vocabulary; particles are generated even on mobile.

---

## 6. Cross-cutting summary for the two project goals

### Redesign (museum-quality) — current-state facts to build from
- Design vocabulary today = orange gradient pills + colored glow shadows + bouncy hover transforms + fade-to-black video loops + particles, over a brown-black background, in one system serif. Every page repeats this from its own inline stylesheet; there are no tokens, no shared components beyond `base.css` utilities.
- Strong assets already present: real postcard scans (contact card, decouvrir frames), the animated-postcard videos, the timeline narrative, and consistently good French copy that only needs restyling, not rewriting.
- Structural to-dos surfaced by this audit: introduce loaded webfonts + CSS variables; consolidate the 5 inline `<style>` blocks (~1,500 lines) and navbar CSS into cached files; delete the 3 dead CSS files; remove `user-select:none`; add `prefers-reduced-motion`; unify light/dark surface strategy (home's cream section is currently the outlier); fix keyboard/touch access on decouvrir and contact.

### OVH migration touchpoints visible from these pages
- Home hero streams `MEDIA_URL/animated_cp/*.mp4` resolved by per-request filesystem probing (`core/models.py:268-297`) after a random-order DB scan (`views.py:1212-1214`) — on OVH this wants: media on object storage or a dedicated Nginx-served volume with long-cache headers, URL resolution from DB fields instead of `Path.exists()` loops, and ideally poster images + preload metadata for the carousel.
- `decouvrir` view hardcodes `/static/...` URLs in Python (`views.py:1364-1396`) — breaks under hashed/manifest static storage or a CDN prefix.
- Fallback video in git at `static/video/Annimate_CPA_optimized.mp4` — static-vs-media split should be revisited when storage moves.
- YouTube dependency on decouvrir could be eliminated by self-hosting those 6 animations alongside the migrated media.
- GA-without-consent (`base.html:13-19`) should be addressed at the same time as the hosting change.



## Issues (flat list)

- Rickroll placeholder in production: painting 'Accident de l'archevêché' opens YouTube ID dQw4w9WgXcQ (Never Gonna Give You Up) — core/views.py:1372
- Dead stylesheets: static/css/home.css, presentation.css and contact.css are referenced nowhere (grep: zero matches); presentation.css re-declares live class names (.presentation-title, .highlight-box, .timeline, .discover-btn) with conflicting values vs templates/presentation.html:182-463 — silent conflict if ever relinked
- Contact 5c-stamp trap: selecting the 5c stamp applies visually but permanently disables submit with zero feedback (templates/contact.html:533, checkFormReady 553-564) — silent failure with no hint or aria-live
- Contact form collects no sender email/name (core/forms.py:9-20 — fields=['message']); anonymous visitors cannot be replied to; admin email only gets IP (core/views.py:236-259)
- Contact success overlay is position:fixed with no close button, no auto-dismiss, no backdrop dismiss — permanently covers the page until reload (templates/contact.html:101-107, 444-456)
- Forced 3-second fake loading screen once per day with no skip control; progress and status messages are simulated (templates/intro.html:232-248; redirect logic core/views.py:1159-1177, 1205-1209)
- intro.html redirect uses unvalidated ?next= param in window.location.href (templates/intro.html:247, core/views.py:1201) — open-redirect vector; needs url_has_allowed_host_and_scheme
- Global user-select:none on body blocks all text selection sitewide (static/css/base.css:314-320, mis-commented 'Disable right-click')
- Single system font 'Bookman Old Style' forced on every element via * selector (static/css/base.css:3-8); it is Windows-only so most visitors get Georgia; the handwriting font 'Dancing Script' used by contact (templates/contact.html:211) is never loaded — no webfonts anywhere
- [class*="animate-"]{opacity:0} makes content invisible unless CSS animations run; no prefers-reduced-motion support in the entire project (static/css/base.css:177-179; duplicated in home.html:708, decouvrir.html:394)
- Animation utility classes/keyframes defined 4+ times with different durations: base.css:136-174 (0.5-0.7s) vs home.html:704-718 (0.8s) vs decouvrir.html:391-398 vs presentation.html:406-410
- Home hero videos resolved by per-request filesystem probing (up to ~80 Path.exists() calls per postcard, core/models.py:268-297) after Postcard.objects.order_by('?')[:30] (core/views.py:1212-1214) — expensive and incompatible with object-storage media on OVH
- decouvrir view hardcodes '/static/images/decouvrir/...' URL strings in Python instead of static()/staticfiles storage (core/views.py:1364-1396) — breaks under hashed storage or CDN prefix on OVH
- decouvrir painting items are div+onclick with no tabindex/role/keyboard handler; titles and play affordance are hover-only so touch users see unlabeled frames; modal lacks focus trap and aria-modal (templates/decouvrir.html:19-23, 210-228, 43-56)
- Full YouTube embed (not youtube-nocookie) + Google Analytics loaded without any consent mechanism — GDPR/CNIL exposure for a French site (templates/decouvrir.html:60, templates/base.html:13-19)
- Contact postcard layout is aspect-ratio-coupled hacks: textarea margin-top:38% / height:calc(100% - 38%) with 'ADJUSTED/KEY FIX' comments; breaks if Cpa_Vierge.jpg changes (templates/contact.html:204-220, 288-300)
- ~1,500 lines of page CSS + ~500 lines of JS shipped inline per page (home.html:105-732, contact.html:111-611, decouvrir.html:62-399, presentation.html:182-463, navbar.html:298-866) — nothing cacheable, repeated on every request
- 15+ console.log/console.error calls left in the production home carousel JS (templates/home.html:146,217,222,243,258,266,272,276,285,296,316,339,363)
- Contact/stamp/signature controls are img+onclick only — no keyboard access, no labels, no state announcement; textarea has placeholder instead of label; maxlength 500 with no counter (templates/contact.html:31-38, 68-86)
- Video indicator dots carry English aria-label 'Video N' on a French site; hero video has no accessible name (templates/home.html:197, 18-20)
- Naming inconsistency: page titled 'La Galerie' lives at /decouvrir/ while a second gallery 'CP Animées' (animated_gallery) exists — confusing IA (templates/decouvrir.html:5,11; core/views.py:48,51)
- Home mobile media query hard-sets hero-title to 1.8rem, defeating the fluid clamp() defined at home.html:518 (templates/home.html:720-721)
- decouvrir loads both Off and Clic PNGs eagerly for all 6 frames with no loading=lazy and no width/height attributes → doubled payload and CLS (templates/decouvrir.html:24-27)
- Justified text (text-align:justify) on narrow measures causes rivers: home welcome paragraphs (templates/home.html:637) and presentation cards squeezed into 3 columns ≥768px (templates/presentation.html:296, 413-416)
- Presentation page for a postcard museum contains zero postcard imagery — only line-icon SVGs; unused asset static/images/cp_bg_présentation.jpg (accented filename, URL-encoding risk) hints at abandoned intent (templates/presentation.html:30-98)
- base.html has no meta description / Open Graph / canonical tags; footer lacks mentions légales required for a French site (templates/base.html:4-19, 36-38)
- Navbar is an opaque saturated-orange fixed bar with icon-only links (title-attribute tooltips only) and a per-page changing brand text via page_title block (templates/partials/navbar.html:10, 28-83, 392-401)
- Modal close button positioned outside the panel (top:-15px right:-15px) can clip at viewport edges on small screens (templates/decouvrir.html:286-302)
- intro splash background (#1a1a1a→#202020 grey) does not match the site's #1a1208 brown theme, and its glowing app-icon fish logo clashes with the museum positioning (templates/intro.html:11-12, 80-97)


## Quick wins

- Replace the rickroll video_id at core/views.py:1372 with the real 'Accident de l'archevêché' animation ID (1-line fix)
- Delete the three dead stylesheets static/css/home.css, static/css/presentation.css, static/css/contact.css to remove the class-name-collision landmine before restyling
- Load 'Dancing Script' (or a licensed handwriting face) in base.html — instantly restores the manuscript effect the contact postcard was designed around (templates/contact.html:211)
- Add feedback for the 5c stamp on contact: a one-line hint + aria-live message when the wrong tariff is applied (templates/contact.html:519-536) — removes the page's silent dead-end
- Give the contact success overlay a close button and auto-dismiss (templates/contact.html:101-107)
- Add a 'Passer' (skip) link to intro.html and/or cut the redirect timer from 3000ms to ~1200ms (templates/intro.html:246-248)
- Remove user-select:none from body (static/css/base.css:314-320) — restores copy/paste sitewide at zero risk
- Strip the ~15 console.log calls from the home VideoCarousel (templates/home.html:105-396)
- Add loading='lazy' + explicit width/height to the 12 decouvrir frame images (templates/decouvrir.html:25-26) to halve initial payload and stop CLS
- Switch the YouTube embed to youtube-nocookie.com and add rel=0 (templates/decouvrir.html:60, 83-92) as an interim GDPR improvement before self-hosting the 6 videos on OVH
- Make decouvrir paintings keyboard-accessible: tabindex='0', role='button', Enter/Space handler on .painting-item, and show the title caption persistently below each frame instead of hover-only (templates/decouvrir.html:19-37, 210-228)
- Translate aria-label 'Video N' to French and add an aria-label to the hero video (templates/home.html:18, 197)
- Fix text-align:justify → left on home welcome paragraphs and presentation card text (templates/home.html:637, templates/presentation.html:296)
- Define the palette once as CSS custom properties in base.css (#b5600b, #d1872c, #ffc168, #1a1208, #2d1f0d, #f5f0e8) and reference them — prerequisite that makes the full overhaul cheap
- Add a global 'prefers-reduced-motion: reduce' block that sets [class*='animate-'] to opacity:1/animation:none (static/css/base.css:177-179) — fixes both motion sensitivity and the invisible-content failure mode
- Validate intro's ?next= with django.utils.http.url_has_allowed_host_and_scheme before rendering it into the redirect (core/views.py:1198-1202)
- Add meta description + Open Graph tags to base.html head (templates/base.html:4-10)