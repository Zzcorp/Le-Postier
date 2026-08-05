# Audit — Expérience de navigation de la collection (browse / gallery / animated_gallery)

Project: `C:/Users/mathe/Documents/CODING/Empire/le-postier` (Django 4.2, French UI, dark brown/amber theme). All paths below are relative to that root unless absolute.

---

## 1. Page inventory & routing

| Page | URL | View | Template | CSS |
|---|---|---|---|---|
| Parcourir (browse) | `/parcourir/` (`core/urls.py:11`) | `core/views.py:1234` | `templates/browse.html` (4072 lines) | **inline `<style>` only** (browse.html:2674-4071); `static/css/browse.css` is **never linked by any template** (verified by grep — no `browse.css` reference in any HTML) |
| CP Animées | `/cp-animes/` (`core/urls.py:12`) | `core/views.py:1300` | `templates/animated_gallery.html` (1587 lines) | inline `<style>` (814-1586) |
| La Galerie | **NOT ROUTED** — `views.gallery` (`core/views.py:1342`) has no entry in `core/urls.py` | `core/views.py:1342` | `templates/gallery.html` (416 lines) | `static/css/gallery.css` (linked at gallery.html:4-6) **plus** a conflicting inline `<style>` duplicate (gallery.html:118-415) |

The navbar item labelled "La Galerie" actually points to `decouvrir` (`templates/partials/navbar.html:61`), not to the `gallery` view. `gallery.html` + `gallery.css` + `views.gallery` are dead code, and even if routed the page would render blank (see §4).

---

## 2. The browse view (`core/views.py:1234-1297`)

### Context variables provided
`postcards` (full list), `themes` (first 20, :1241), `query`, `total_count`, `displayed_count`, `user`, `user_likes` (views.py:1282-1290).

### What the view does
- Reads **only** `keywords_input` from GET (views.py:1237). **It never reads `sort`, `order`, `rarity`, or `animated`** — yet browse.html renders a full filter panel that submits exactly those params (hidden inputs at browse.html:161-164, `applyFilters()` at 743-749). **The entire filter/sort panel is a placebo**: submitting it triggers a full page reload that changes nothing.
- Because `current_sort`/`current_order`/`current_rarity`/`current_animated` are never put in context, all `{% if current_sort == ... %}` active-states in the panel (browse.html:211-296) always show defaults. Worse, the "filters active" green dot condition `{% if current_rarity or current_animated or current_sort != 'number' %}` (browse.html:172) evaluates `'' != 'number'` → **the dot is permanently shown even with no filters**.
- **No pagination whatsoever**: `postcards_list = list(postcards)` (views.py:1263) — the entire collection with images is rendered.
- Search: `search_postcards()` (views.py:437-542) loads **all** postcards into Python (`base_queryset.values(...)`, :463) and scores each row in a Python loop (467-509) with accent-stripping, token matching, then rebuilds ordering with `Case/When` (537-540). O(N) Python per request, no DB index used for matching. Six `print()` debug statements run in production (views.py:455-457, 465, 516-529; also 1255).
- Every search is logged to `SearchLog` with the visitor's IP (views.py:1249-1254).
- On exception, the **full traceback is returned to the visitor as HTML** (views.py:1297; same pattern at 1339 and 1351).
- Sorting is forced to `order_by('number')` (views.py:1260) — `number` is a CharField (models.py:184) so ordering is lexicographic.

### Media URL resolution cost (critical for OVH migration)
`Postcard` has **no stored image fields**. Every `get_vignette_url()/get_grande_url()/get_dos_url()/get_zoom_url()` call runs `_find_local_image()` (core/models.py:225-252) which probes the filesystem with up to **16 `Path.exists()` calls** (8 extensions × 2 naming schemes). `get_animated_urls()` (models.py:268-297) adds up to ~12+ more `exists()` calls. In browse.html each card invokes these methods ~12 times (data-attrs at 364-369, `{% with %}` at 373, badge check 393, video-link check 427, and again in the JSON dump 623-629). **For a 500-card collection this is on the order of 50,000+ `stat()` syscalls per page view**, against Render's network-mounted persistent disk (`/var/data/media`, `core/middleware.py:18-22`, `le_postier/settings.py:112-122`). This is the single largest server-side cost of the browse page and the top item to fix in the VPS migration (store URLs in DB columns or a cached manifest; serve media via nginx or OVH Object Storage instead of the Django `MediaServeMiddleware` at `core/middleware.py:25-147`, which serves every image/video through Python with only a 24h cache header, :90, and a per-request case-insensitive directory-walk fallback, :102-147).

---

## 3. browse.html — template & full JS behavior catalog

### 3.1 Payload duplication
Each postcard is serialized **twice**: once as DOM data-attributes on `.postcard-card` (browse.html:359-370, including `data-grande`, `data-dos`, `data-zoom`, `data-video-url`) and again in the `allPostcardsData` JS array (616-632, same URLs + `likes_count` + lowercased keywords). For a large collection the HTML document alone is multiple MB. `data-title="{{ postcard.title|escapejs }}"` (362) uses JS escaping in an HTML attribute — titles with apostrophes render as literal `\u0027` in the attribute.

### 3.2 Loading overlay — artificial delay
- Overlay markup 8-18, shown instantly via IIFE (598-605), `z-index:99999` (2681).
- `MIN_LOADING_TIME = 2500ms (1800ms when searching)` (614) — the spinner+fake-percentage overlay (`LoadingManager` 2517-2596, eased fake progress to 90%, 2539-2562) is **deliberately held for 2.5 s even if the page is ready**. Hidden on `window.load` (2660-2664) with a 5 s fallback (2667-2671). Every visit to the main collection page costs a mandatory 2.5-second wait.

### 3.3 Search UI
- Form 158-195 → GET to `/parcourir/` → **full page reload** (and another 1.8 s forced loader). No debounced live search: `SimpleSearchEngine` (975-995) only toggles the clear button. `clearSearch()` = `window.location.href` reload (1003-1005).
- Two identical client-side search functions `searchPostcardsClient` are defined twice (869-918 and 923-970) — **both are dead code, never called**.
- Result info line 313-320 shows count; footer count 471-473.

### 3.4 Client pagination — dead code
`ITEMS_PER_PAGE = 50` (611), `renderCurrentPage()` (1010-1055), `createPostcardCard()` (1057-1132), `renderPagination()` (1134-1194), `goToPage()` (1196-1202), `initLazyLoading()` (1204-1231). **Nothing ever calls `renderCurrentPage()`** — init (2643-2657) only instantiates search/decoration classes. Result: the pagination container (455-458) stays empty and **the full server-rendered grid of every postcard is shown at once**. Additional latent bugs if ever activated: `createPostcardCard` resets likes with `const userLikes = new Set()` (1072 — always empty, liked state lost), and re-inserts titles via template literals.

### 3.5 Lazy loading
Images use `data-src` + `loading="lazy"` + placeholder spinner (375-381). Two competing IntersectionObserver implementations: `ImageLoader` (2476-2512, used on initial load) and `initLazyLoading` (1204-1231, only reachable from dead pagination). `rootMargin: 100px`. Card image area has `aspect-ratio: 4/3` (3577) so grid layout shift is controlled, but `object-fit: cover` (3578) **crops the postcards** (real CPA cards are ~1.55:1 landscape) — the artifact is never shown whole in the grid.

### 3.6 Detail popup (front/back flip)
- Markup 476-538; `showDetail(id)` 2314-2353 reads **only local `allPostcardsData`** — it **never calls `/api/postcard/<id>/`**. Consequences: (a) `views_count` is never incremented from browse (increment only lives in `get_postcard_detail`, views.py:1440-1441); (b) **the very_rare gating in `get_postcard_detail` (views.py:1457-1481, member-card placeholder :1465) is completely bypassed** — grande/dos/zoom/video URLs for very-rare cards are already in the DOM/JS for anonymous visitors; (c) description/keywords/rarity returned by the API (views.py:1483-1498) are never displayed — popup shows only title + number (534-537).
- Flip to verso 2362-2378 (`dos_url`, instant `img.src` swap — no flip animation despite the rotate icon); prev/next 2380-2425 navigate `filteredPostcards` (= all cards, since client filtering never runs); keyboard ←/→/Esc 2618-2623; overlay click closes 2632-2636. Nav arrows are hidden on mobile (3983) with no swipe substitute.

### 3.7 Zoom modal
- Markup 540-589 (with emoji instruction bar "🖱️ Molette…" 586); `zoomState` 1825-1836; `showZoom` 1838-1873 uses the **local** `zoom_url` — the `/api/postcard/<id>/zoom/` endpoint (views.py:1506-1528) with its rarity gate and `zoom_count` increment is **never called from browse**. Full-featured interactions: wheel-to-cursor zoom (1912-1933), drag pan (1935-1964), double-click 2× (1966-1987), pinch zoom (1989-2045), keyboard +/−/0/F/Esc (2047-2073), toolbar buttons (554-583). Zoom listeners added/removed on open/close (1883-1910). Loads the full `Zoom` image in one shot — no tiling/progressive loading for large scans.

### 3.8 Cinema / diaporama
- Modal markup 20-100 (hardcoded placeholder counter "1 / 50" at 41), launcher 323-342. Logic 2137-2308: modes static/animated/mixed (`buildCinemaList` 2181-2199), 4-second `setInterval` autoplay (2142, 2293-2298), arrow/space/Esc keys (2603-2610). Slides set `img.src`/`video.src` directly per step — no preloading of the next slide, so each advance shows the loading spinner on slow connections. Uses `grande_url` full-size images.

### 3.9 Likes
`toggleLike` (2430-2465) POSTs `/api/postcard/<id>/like/` with CSRF token inlined as a JS global (610). Server (`like_postcard`, views.py:1531-1590) supports anonymous session likes, does an **IP geolocation lookup on every like** (1545), and updates `likes_count` non-atomically (`postcard.likes_count += 1` … `save`, 1562-1580 — race-prone; no `F()` expressions). No optimistic UI: icon updates only after the round-trip; likes count is not displayed on grid cards at all (only inside the popup, 510).

### 3.10 Decorative animation systems (the "river" theme)
Five independent, always-running animation systems on the browse page:
1. `FloatingKeywords` (1236-1380): 15 floating keyword "bubbles" animated via rAF mutating `left/top/border-radius` (1344-1348 — layout-thrashing properties, not transforms). Clicking one plays a bubble-pop (1383-1416) then **submits the search form = full reload** (1375-1378). Keyword list is hardcoded (635-667) + themes (668-670).
2. `AquaticLifeManager` (1421-1601): 7 SVG fish + 2 seahorses, rAF loop.
3. `SilureManager` (1606-1737): 2 long SVG catfish, rAF loop.
4. `LightParticles` (1742-1820): 30 glowing dots, rAF loop.
5. `main.js:7-55` injects **50 more `.particle` divs** into `<body>` on `/parcourir/` — but their styles live only in the never-loaded `static/css/browse.css` (91-155), so they are **invisible unstyled divs**; and since the CSS animation never runs, `animationend` (main.js:43) never fires — 50 dead nodes.
Plus two animated SVG wave layers (113-148) and a fixed gradient background (2748-2759). Only `FloatingKeywords` pauses when off-screen (1357-1365); the other rAF loops run forever, even with the tab section scrolled away. No `prefers-reduced-motion` handling anywhere. Total: 4 concurrent rAF loops + ~60 animated DOM nodes — meaningful battery/CPU drain, and aesthetically a cartoon aquarium rather than a museum.

### 3.11 CSS architecture (browse)
~1,400 lines of CSS inline in the template (2674-4071). Not cacheable, duplicated concepts with other pages, z-index escalation (loading 99999, bubbles 9998, zoom 6000, cinema 5000, popup 3001/3000, filter 100/99). `static/css/browse.css` (483 lines) targets a **previous generation of the page** (`#page_top`, `#keywords_input`, `.cp_result`, `#cinema-clape`, `.glowing-word`, `#popup_detail`) — 100% dead.

### 3.12 Responsive & a11y (browse)
- Breakpoints 768/480 (3969-4070): grid drops to `minmax(150px,1fr)` then 2 columns; popup nav arrows removed on mobile with no swipe.
- Cards are `<div onclick>` (359-370): not focusable, no keyboard access, no `role`/`aria`. Action buttons appear only on hover overlay (3620-3628). Modals have no focus trap, no `aria-modal`, no `role="dialog"`. Dozens of inline `onclick=` handlers (CSP-hostile).
- `base.css:315-319` sets `user-select:none` on body and `main.js:4` blocks the context menu globally — hostile to visitors and trivially bypassed.
- Text at `rgba(255,255,255,0.5-0.6)` on dark brown is low-contrast (e.g. 3242, 3283, 3439).

---

## 4. gallery.html — broken and unreachable

- **Not routed** (no entry in `core/urls.py`); navbar "La Galerie" goes to `decouvrir` (navbar.html:61).
- **Would render blank if routed**: template reads `{{ postcard.vignette_url }}`, `{{ postcard.grande_url }}` (gallery.html:30, 45) but the model exposes only *methods* `get_vignette_url()` etc. (models.py:254-266) — no such attributes exist, so Django resolves them to `''`; `onerror="this.parentElement.style.display='none'"` (32) then hides items.
- View uses `order_by('?')[:50]` (views.py:1345) — expensive random ordering, different set each load, no pagination, traceback leaked on error (1351).
- Duplicate styling: external `gallery.css` AND an inline `<style>` (118-415) redefining the same classes with drifted values (e.g. `.filter-btn` padding 8/20 in css vs 10/25 inline; different `.gallery-lightbox` details). Inline wins by cascade order.
- Client-only rarity filter (77-95, `display:none` toggling), simple lightbox (98-115, Esc close). Items have no fixed aspect ratio (`height:auto`, gallery.css:62-67) → layout shift; hover-scale + slide-up overlay pattern.
- Decision needed in the overhaul: delete this page, or rebuild it as the flagship "museum wall" view (it's currently the only masonry-ish presentation).

## 5. animated_gallery.html (`/cp-animes/`)

### View (`core/views.py:1300-1339`)
Iterates **all** postcards ordered by `-likes_count` calling `get_animated_urls()` per postcard (1303-1312) — ~10-90 file `exists()` probes each — until 100 animated ones are found. `total_count` is the number found (1333), labeled "animations disponibles".

### Template behavior
- Loading overlay (8-22) with `LoadingManager` (403-444); progress counts poster `onload` (784-801) against `totalCount`, but posters use `loading="lazy"` (84) so off-screen images never load and the counter stalls — masked by a 1.5 s hide (804-806) + `window.load` (809-811).
- Cards: `data-vignette` actually holds `get_grande_url` (76 — misnamed); poster `<img src=…>` eager attribute + `loading="lazy"`; `<video preload="none" data-src>` (87-93).
- `VideoHoverManager` (249-398): 150 ms hover-intent (273-275), lazy-assigns `video.src` on first hover, crossfades poster↔video, pauses+rewinds on leave (375-397), touch tap toggles (288-300). Good pattern. No cap on number of simultaneously-loaded videos over a session.
- Modal (`openAnimatedModal` 472-554): **the only place the gated `/api/postcard/<id>/` API is called** (508) — fetches all `animated_urls`, builds video tabs when multiple (519-532), `loadModalVideo` (556-601) with error fallback and a 10 s "Chargement lent…" fallback opening the raw file in a new tab (593-600). `autoplay` + `controls` + `loop` (175). Esc closes (752-757). `?highlight=<id>` auto-opens after 800 ms (762-771) — used by browse's video buttons (browse.html:428, 1119).
- Sorts (41-65 + 449-467): "Plus aimées" works (dataset.likes numeric); **"Récentes" does nothing** — `sortGallery` has no `recent` branch (457-464, comparator returns 0); "Par numéro" uses `localeCompare` on strings (461) → "10" sorts before "2".
- Likes: `toggleLike` (641-681) with `is_animated=true`; modal like syncs (672-676).
- Suggestion flow (692-747): textarea 500 chars, validation via **`alert()`** (712, 732, 736), success modal (226-237).
- Header uses emoji "🎬" (28); ~770 lines of inline CSS (814-1586); modal goes fullscreen under 768px (1570-1576).

---

## 6. Rarity gating — actual state

- Gate logic exists only in `get_postcard_detail` (views.py:1457-1481: anonymous or non-`can_view_very_rare` users get `/static/images/Carte_Membre_4.jpeg` placeholders + `is_restricted: True`) and `zoom_postcard` (1511-1526).
- **Browse never invokes either endpoint** — `showDetail`/`showZoom`/cinema all use URLs already embedded server-side for every card regardless of rarity or auth (browse.html:359-370, 616-632). Anyone can view/zoom/download very-rare scans from `/parcourir/`. The gate is only effective inside the animated-gallery modal fetch (animated_gallery.html:508). If the tiered-membership concept matters, gating must move server-side (don't render restricted URLs; sign/proxy media URLs — natural to fix during the OVH media redesign).

## 7. Analytics & counters side-effects

- `AnalyticsTrackingMiddleware` (core/middleware.py:150-374) performs an IP geolocation lookup + up to 3 DB writes (PageView, VisitorSession, RealTimeVisitor) on **every HTML GET**, synchronously in-request.
- `views_count` only increments via the API browse never calls; `zoom_count` only via the zoom API browse never calls → both counters are effectively frozen for the main page, yet "Vues" is offered as a sort option in the (non-functional) filter panel (browse.html:229-235).

## 8. Design-language snapshot (for the museum-quality overhaul)

- Global font: `"Bookman Old Style", Georgia, serif` applied to **everything** via `*` (base.css:3-8); no typographic hierarchy, no display face, no webfonts.
- Palette: background `#1a1208`→`#3d2a12` gradients; accents `#b5600b` / `#d1872c` / `#ffc168`; success green `#22c55e`; like red `#ff6b6b`. Heavy gradient pills, 20-25px border radii, hover `scale()`/`translateY` transforms on nearly every element.
- Tone: aquarium cartoon (fish, seahorses, catfish, bubbles, waves), emojis in UI copy, fake loading percentages, "Désolé, aucune carte trouvée". The collection imagery itself is cropped to 4:3 thumbnails with actions hidden behind hover overlays; titles/numbers only on hover; no descriptions, dates, provenance, or rarity shown in the browsing surface even though the data exists (`description`, `keywords`, `rarity` — models.py:186-189).
- Navbar reuses the `page_title` block as the brand text (navbar.html:10 + browse.html:5), so the site name is replaced by "Rechercher"/"La Galerie"/"CP Animées" per page.

## 9. Migration-relevant facts (Render → OVH VPS)

- Media root switches on `RENDER` env or `/var/data` existence (settings.py:112-122, models.py:13-21, middleware.py:18-22) — three duplicated implementations of `get_media_root`.
- Media is served by Django (`MediaServeMiddleware`) in production with `Cache-Control: max-age=86400` (middleware.py:90) and a case-insensitive directory-walk fallback per miss (102-147). Static goes through WhiteNoise (settings.py:35,103).
- Image derivative structure on disk: `media/postcards/{Vignette,Grande,Dos,Zoom}/NNNNNN.{jpg,…}` and `media/animated_cp/NNNNNN[_i].mp4` — discovered at request time by extension probing (models.py:239-250, 280-295). No DB record of which files exist beyond the boolean `has_images` (models.py:194).
- For OVH: store per-derivative URLs/paths on the model (or a manifest table populated by a sync command), serve `/media/` directly via nginx (or OVH Object Storage + CDN), and this removes both the stat-storm (§2) and the Python media-serving path in one move; signed URLs would also make rarity gating enforceable (§6).



## Issues (flat list)

- Filter/sort panel is non-functional server-side: browse view reads only 'keywords_input' (core/views.py:1237) while the panel submits sort/order/rarity/animated (templates/browse.html:161-164, 743-749) that are silently ignored; context vars current_sort/current_order/current_rarity/current_animated are never provided (core/views.py:1282-1290)
- Filter 'active' green dot always shows: `{% if ... current_sort != 'number' %}` with undefined current_sort evaluates '' != 'number' = True (templates/browse.html:172)
- No pagination anywhere on browse: view renders the entire collection (core/views.py:1263); the client-side pagination system (ITEMS_PER_PAGE=50, renderCurrentPage/renderPagination/goToPage, templates/browse.html:1010-1202) is dead code — never invoked at init (2643-2657), so the full grid renders at once
- Artificial 2.5s (1.8s on search) forced loading overlay on every browse visit: MIN_LOADING_TIME at templates/browse.html:614, enforced in LoadingManager.hide (2564-2595)
- Filesystem stat storm: no stored image URLs — every get_*_url call probes disk with up to 16 Path.exists() (core/models.py:225-252) and get_animated_urls up to ~12+ more (268-297); browse invokes ~12 such methods per card (browse.html:364-369, 373, 393, 427, 623-629) → tens of thousands of stat() calls per page view on Render's network disk
- Rarity gating bypassed on browse: grande/dos/zoom/video URLs of ALL cards (incl. very_rare) are embedded in DOM and JS for anonymous users (templates/browse.html:359-370, 616-632); showDetail/showZoom never call the gated APIs get_postcard_detail/zoom_postcard (browse.html:2314-2353, 1838-1873 vs core/views.py:1457-1481, 1511-1526)
- views_count and zoom_count never increment from browse because the incrementing API endpoints are never called there (core/views.py:1440-1441, 1519-1520), yet 'Vues' is a sort option in the (dead) filter panel (templates/browse.html:229-235)
- gallery page is dead and broken: views.gallery (core/views.py:1342) is not routed in core/urls.py; template reads non-existent attributes postcard.vignette_url/grande_url (templates/gallery.html:30, 45 — model only has get_vignette_url() methods, core/models.py:254-266) so every img src resolves to '' and onerror hides all items (gallery.html:32); view also uses order_by('?') (core/views.py:1345)
- Server-side search is O(N) Python: search_postcards loads every postcard row and scores in a loop per request (core/views.py:463-509) and leaves 6+ print() debug statements in production (455-457, 465, 516-529, 1255)
- Production error pages leak full tracebacks to visitors in browse/animated_gallery/gallery (core/views.py:1297, 1339, 1351)
- Full page reload for every interaction: search submit (templates/browse.html:159), keyword-bubble click (1375-1378), clear search (1003-1005), and filter apply (743-749) all reload /parcourir/ and re-trigger the forced loading overlay
- Duplicate dead JS: searchPostcardsClient defined twice, both never called (templates/browse.html:869-918 and 923-970); two competing lazy-load implementations (initLazyLoading 1204-1231 vs ImageLoader 2476-2512)
- Five concurrent decorative animation systems on browse: FloatingKeywords + AquaticLife (7 fish, 2 seahorses) + Silure (2 catfish) + LightParticles (30 dots) = 4 rAF loops mutating left/top (layout thrash, templates/browse.html:1236-1820), plus main.js:7-55 injecting 50 invisible unstyled particle divs (their CSS lives in the never-loaded static/css/browse.css:91-155); no prefers-reduced-motion handling anywhere
- static/css/browse.css (483 lines) is entirely dead — targets a previous DOM (#page_top, .cp_result, #cinema-clape, .glowing-word) and is not linked by any template
- gallery.html double-styling: links static/css/gallery.css (gallery.html:4-6) AND redefines the same classes inline with drifted values (gallery.html:118-415)
- animated_gallery 'Récentes' sort button does nothing (no 'recent' branch in sortGallery, templates/animated_gallery.html:457-464) and 'Par numéro' uses string localeCompare so '10' < '2' (461)
- animated_gallery loading progress counter stalls because posters are loading='lazy' (templates/animated_gallery.html:84) while progress counts all poster onloads against totalCount (784-801); masked by a 1.5s timeout (804-806)
- animated_gallery view scans all postcards with per-row filesystem probing to find 100 animated ones on every request (core/views.py:1303-1312)
- likes_count updated non-atomically (read-modify-write, no F() expressions) in like_postcard (core/views.py:1562-1580); every like also triggers a synchronous IP geolocation lookup (1545)
- Detail popup shows only title+number (templates/browse.html:534-537); description, keywords, and rarity exist in the model and API (core/models.py:186-189, core/views.py:1483-1498) but are never surfaced in the browsing experience
- Grid thumbnails crop the artwork: object-fit:cover in a 4:3 box (templates/browse.html:3577-3578) truncates landscape postcards; captions/actions only appear on hover overlay (3620-3628) — nothing visible at rest, hostile to touch
- Accessibility: cards are div[onclick] with no keyboard focus/roles (templates/browse.html:359-370); modals lack focus traps/aria-modal; dozens of inline onclick handlers; body user-select:none (static/css/base.css:315-319) and global context-menu blocking (static/js/main.js:4)
- escapejs misused for an HTML attribute: data-title="{{ postcard.title|escapejs }}" renders ' sequences for apostrophes (templates/browse.html:362)
- ~1,400 lines of CSS and ~2,000 lines of JS inline in browse.html (2594-4071) — uncacheable, unversioned, duplicated across pages; z-index escalation to 99999
- Cinema/diaporama has a hardcoded '1 / 50' placeholder (templates/browse.html:41), no next-slide preloading (2221-2267), and loads full-size grande images per 4s tick
- Media served through Django in production via MediaServeMiddleware with only 24h cache and per-miss case-insensitive directory walks (core/middleware.py:25-147); get_media_root duplicated 3× (core/middleware.py:18, core/models.py:13, le_postier/settings.py:112-122) — key redesign target for the OVH move
- Navbar brand text is replaced by the page title on every page via the page_title block (templates/partials/navbar.html:10, browse.html:5), erasing the site identity
- AnalyticsTrackingMiddleware performs synchronous IP-geolocation + up to 3 DB writes on every HTML GET (core/middleware.py:150-374), adding latency to each browse render
- Anonymous visitors' liked-state is lost if the dead client pagination ever activates: createPostcardCard rebuilds cards with an always-empty likes Set (templates/browse.html:1072)
- suggest/validation UX uses native alert() dialogs (templates/animated_gallery.html:712, 732, 736)


## Quick wins

- Delete MIN_LOADING_TIME (browse.html:614) and hide the overlay on DOMContentLoaded — removes a mandatory 2.5s wait from the most important page for one line of change
- Implement server-side pagination in views.browse (Django Paginator, ~50/page) and drop the allPostcardsData JSON dump — collapses a multi-MB document and the dead client-pagination code can be deleted wholesale (browse.html:1010-1231)
- Cache media URLs: add vignette/grande/dos/zoom/video path columns (or a JSON manifest field) populated by a management command, and make get_*_url read them — eliminates ~50k stat() calls per browse render (core/models.py:225-297); prerequisite anyway for OVH object-storage/nginx serving
- Wire the filter panel to the view: read sort/order/rarity/animated in views.browse and pass current_* into context (core/views.py:1237, 1282-1290) — the entire UI already exists; also fixes the always-on green dot (browse.html:172)
- Route or remove the gallery page: one path() line + replacing postcard.vignette_url with postcard.get_vignette_url in gallery.html:30/45 revives it; otherwise delete gallery.html, gallery.css and views.gallery
- Delete dead code in one sweep: static/css/browse.css, both searchPostcardsClient copies (browse.html:869-970), initLazyLoading (1204-1231), and the invisible water-particles injection for /parcourir/ in main.js:50-55
- Stop leaking tracebacks and remove print() debug from browse/search/animated views (core/views.py:455-529, 1255, 1297, 1339, 1351) — replace with logger calls and a friendly error template
- Make showDetail fetch /api/postcard/<id>/ (endpoint already exists and is gated): restores view counts, enforces very_rare gating, and unlocks showing description/rarity in the popup — the API already returns them (core/views.py:1483-1498)
- Add a 'recent' branch (sort by created_at delivered as data-created attr) and numeric compare to sortGallery (animated_gallery.html:457-464)
- Wrap all decorative animation startup in a matchMedia('(prefers-reduced-motion: reduce)') check and pause the 3 unconditional rAF loops when off-screen (browse.html:1421-1820) — instant CPU/battery win and an accessibility fix
- Use F('likes_count')+1/-1 in like_postcard (core/views.py:1562-1580) to fix the counter race
- Switch grid thumbnails from object-fit:cover to contain (or use the card's native aspect ratio) so the postcards are shown whole (browse.html:3577-3578) — single-property change with major perceived-quality impact for a collection site