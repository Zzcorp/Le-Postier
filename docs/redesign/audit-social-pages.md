# Social Features Audit — "La Poste" & Profile (Le Postier)

Scope: `templates/la_poste.html` (3,009 lines), `templates/profile.html` (3,512 lines), backing views in `core/views.py` (3,751 lines), models in `core/models.py`, routes in `core/urls.py`. All paths below are relative to `C:/Users/mathe/Documents/CODING/Empire/le-postier/`.

Both pages are single-file monoliths: HTML + inline `<script>` + inline `<style>` in one template. la_poste.html: markup 1–719, JS 721–1312, CSS 1314–3008. profile.html: markup 1–990, JS 992–1650, CSS 1652–3511. Both extend `base.html` which loads only `static/css/base.css` (base.html:8); body font is "Bookman Old Style", Georgia, serif (base.css:7).

---

## 1. La Poste page (`templates/la_poste.html`, view `la_poste` at core/views.py:1626–1673)

### 1.1 View context (views.py:1626–1673)
- `user_has_signature = bool(request.user.signature_image)` (1629) — gates the whole compose flow.
- `preselected_postcard` from `?postcard=` GET param (1632–1638) — **passed to context (1670) but never used anywhere in la_poste.html** (grep confirms no reference). Dead feature.
- `received` / `sent`: last 30 each, `select_related` (1640–1646). `public_postcards`: last 50 public with `prefetch_related('comments')` (1648–1650). `unread_count` (1652–1655).
- Compose picker inventory: `available_postcards = Postcard.objects.filter(has_images=True).order_by('?')[:100]` (1657) and `animated_postcards` = python-side filter of another random 200 for `has_animation()`, cap 50 (1659–1660). **Random ordering means the picker shows a different arbitrary 100-card subset every load; a user can never reliably find a specific card**, and `order_by('?')` is expensive at DB level. Client-side search (la_poste.html:911–921) filters only this loaded subset by title/number.

### 1.2 Page structure (markup)
- Animated background: fixed dark-brown gradient (`#0d0906 → #2d1f0d`, CSS 1325–1340) plus JS-generated decoration: 25 floating emoji (✉️ 📜 🖋️ 📮 🏛️ ⚜️ … la_poste.html:736–757) and 60 "dust particles" (759–774), all animating infinitely (CSS 1343–1389). Museum-quality intent, but emoji at 3–8% opacity with `filter: grayscale(50%)` read as noise and cost continuous compositing.
- Header with mail icon, title, tagline (18–37); green unread pill if `unread_count > 0` (28–36).
- Signature warning banner when no signature (40–61) linking to `{% url 'profile' %}`; amber alert styling (CSS 1449–1503).
- Single primary action "Écrire une carte" (64–75); disabled state + `showSignatureRequired()` modal when no signature (65–66, 694–719).
- Three pill tabs: Reçues (with `tab-badge` count 85–87), Envoyées, Mur Public (78–102); `switchTab()` (779–788) is pure class toggling — no URL hash, no history, state lost on reload (page always reopens on "Reçues").

### 1.3 Received tab (107–171)
- Card grid `repeat(auto-fill, minmax(300px,1fr))` (CSS 1615–1618). Each `.postcard-item`:
  - Vignette `postcard.get_vignette_url` (124); if animated, a `<video muted loop playsinline preload="none" data-src>` overlay (114–123) lazily gets `src` and plays on hover (`initVideoHovers`, 1253–1270); play indicator icon (118–122).
  - Unread: `.unread` class + green "Nouveau" badge (110, 126–128) with green glow border (CSS 1635–1638).
  - Sender row: 38px avatar showing **the sender's signature image** or first letter (139–145) + username (146).
  - "Lire" button → `viewPostcardMessage(id)` (149–155); date `d/m/Y` (156).
- Empty state (161–168).

### 1.4 Sent tab (174–250)
Same card layout; recipient row shows "À {username}" or "Publication publique" (216–220); globe `public-badge` for public cards (193–201); animated badge (202–208); "Voir" button same `viewPostcardMessage`. Empty state offers compose or signature-creation CTA (242–246). **No read-status shown here** (the profile page does show Lu/Non lu — inconsistent).

### 1.5 Mur Public / wall tab (253–342)
- Single-column feed max-width 650px (CSS 1826–1829). Each `.wall-post`: author header (avatar = signature image or initial, 259–265; username + `d/m/Y H:i`, 267–268); image area — for animated, hover-play video declared **twice** (inline `onmouseenter`/`onmouseleave` at 277 *and* `initVideoHovers` listeners, 1253–1270); otherwise full `get_image_url` (286).
- Actions row: "Lire le message" and "N commentaire(s)" toggle (290–304). `{{ postcard.comments.count }}` in the template (302) triggers **one COUNT query per wall post** (50 posts → 50 queries; `prefetch_related` caches `.all()`, not `.count()`).
- Comments block hidden by default via inline `style="display:none"` (306); list renders `comment.user.username`, `comment.message`, date (308–314); form with 500-char input (316–324).
- No likes/reactions on wall posts — comments only.

### 1.6 Compose flow — the postcard-sending wizard (modal 347–574, JS 793–1097)
Three-step modal with step indicator (367–382):

**Step 1 — Carte (386–430):** type toggle "Carte classique" / "Carte animée" (388–403, `setCardType` 882–901, resets any selection); selector preview opens the picker modal (577–635) which has search (589–595, `filterPostcards` 911–921) and two grids (static 598–609, animated 612–633, `loading="lazy"` thumbnails, items labeled only "N° {number}"). `selectPostcard()` (923–950) stores id/title/number/videoUrl, previews image or autoplaying video, enables "Suivant".

**Step 2 — Message (433–499):** a real skeuomorphic postcard — `static/images/Cpa_Vierge.jpg` as background (437) with three absolutely-positioned zones:
- textarea `.compose-message-input` at left 4%/top 42%, 48%×45% (CSS 2298–2312), `maxlength=55` default (446), font `'Dancing Script', cursive, Georgia, serif` (CSS 2308) — **Dancing Script is never loaded** (no Google-Fonts link in base.html:7–8, no @font-face in base.css) so the "handwriting" falls back to generic cursive/Georgia. Same for the message-view modal (CSS 2782, 2817).
- stamp zone top-right (450–455): dashed placeholder until a stamp is applied.
- signature zone right (458–462) rendering `user.signature_image`.

**Stamp choice (467–479, `selectStamp` 955–986):** two options — `5c` → 44 chars, `10c` → 55 chars, images `static/images/Timbre_5c.png` / `Timbre_10c.png`; 10c pre-selected in markup (474) and re-selected on DOMContentLoaded (1310). Selecting a stamp updates `maxChars` display + textarea maxLength (963–964), swaps the applied stamp image (967–976), and **silently truncates an already-typed message** when switching 10c→5c (979–983). Char counter `0/55` under the card (481–483). "Suivant" enabled only when message non-empty (`validateStep2`, 994–997).

**Step 3 — Envoi (502–571):** visibility toggle Privé/Public (504–520, `setVisibility` 1002–1008 shows/hides recipient); recipient input with autocomplete (523–533): debounced 300ms, min 2 chars, `fetch('/api/users/search/?q=…')` (1011–1037); suggestions rendered via `innerHTML` template literal showing `u.username` and **the raw `u.category` slug** (1030) — server returns machine values like `subscribed_verified` (views.py:1900–1906, model choices at core/models.py:30–35), so users see internal codes instead of "Facteur"/"Inscrit - Vérifié". `selectRecipient` fills the input (1039–1042). Summary block (536–554, `updateSummary` 868–877). Submit → `sendPostcard()` (1047–1097): POST JSON to `/api/la-poste/send/` with `{message, recipient|null, visibility, postcard_id, stamp_type, is_animated}` (1069–1083); on success closes modal, toast, **full `location.reload()` after 1.5s** (1090).

Server side `send_postcard` (views.py:1676–1745): re-checks signature (1683–1686); enforces `max_chars = 44 if stamp_type=='5c' else 55` (1691–1699) — note **any other `stamp_type` string is accepted and stored** (model `stamp_type` max_length=10, choices not enforced on `.create()`, models.py:559); recipient required + must exist + not self for private (1706–1716); postcard required (1718–1726); `is_animated` **trusted from the client** (1704, 1735) — a static card can be flagged animated. Creates `SentPostcard` (1728–1736; model at models.py:537–598, `message = TextField(max_length=55)` 558). No rate limiting, no notification to recipient (no email/push — recipient discovers the card only by visiting La Poste).

### 1.7 Viewing cards & messages
- `viewPostcardImage(id, tab)` (1102–1127): lightbox modal (637–653) showing the grid `<img>`'s `src` — i.e. **the vignette, not the large scan, for received/sent cards** (grid imgs use `get_vignette_url`, 124/191) — or the video with controls for animated.
- `viewPostcardMessage(id)` (1139–1187): GET `/api/la-poste/{id}/message/` → `get_postcard_message` (views.py:1748–1779). Server checks privacy (private → sender/recipient only, 1754–1756) and **marks as read as a side-effect of this GET** (1758–1760; the dedicated POST `/api/la-poste/<id>/read/` endpoint, views.py:1849–1859, is never called by any template). Renders the same Cpa_Vierge.jpg postcard back (666–692): message text, stamp image chosen by `stamp_type` (1153–1158), sender signature + name (1160–1170), date. Client removes the card's "Nouveau" badge (1174–1179) but **the header unread pill (28–36) and tab badge (85–87) never decrement until reload**.

### 1.8 Comments JS (1210–1248)
`toggleComments` flips display (1210–1213). `addComment` POSTs to `/api/la-poste/{id}/comment/` (1215–1230); server `add_comment` (views.py:1862–1889) requires public card + ≥2 chars, no auth beyond login, no length cap enforcement server-side (model TextField max_length=500 isn't validated on `.create()`). Success appends the comment with `list.innerHTML += \`…${data.comment.message}…\`` (1235–1242) — **unescaped interpolation (self-XSS / HTML injection into own view; server-rendered comments are escaped by Django, so persistent XSS is blocked, but the pattern is unsafe)**. Failure path: `console.error` only — **the user gets no feedback when a comment fails** (1245–1247); comment count on the button also never updates.

### 1.9 Other la_poste UI machinery
- Toast `showNotification` (1275–1286), 4s auto-remove, message interpolated into innerHTML.
- Escape key closes every modal unconditionally (1291–1299) and backdrop click too (349) — **an in-progress postcard draft is destroyed with no confirmation** (`resetComposeForm` on next open, 808–846).
- Styling: hard-coded sepia/amber palette (`#b5600b`, `#d1872c`, `#1a1208`, `#ffc168`, green `#4ade80` accents), border-radius 16–35px pills, one breakpoint `@media (max-width:768px)` (2944–2988) — tabs stack vertically, grid → 1 column, picker → 3 columns. The compose postcard overlay zones are %-positioned against the JPG (2298–2365) and get no mobile adjustments — **on small screens the writable area is ~150px wide with 14px fixed font**.

---

## 2. Profile page (`templates/profile.html`, view `profile_view` at core/views.py:735–822)

### 2.1 View context (views.py:735–822)
Counts: sent/received/unread `SentPostcard`, likes, suggestions (741–745); connections = distinct union of sent-to + received-from user ids (748–752); `total_views` = count of `postcard_view` UserActivity (755). Lists: 20 liked postcards (768–770), 10 sent (773–775), 10 received (778–780), 15 recent activities (803). Epistolary connections built in a **Python loop with 4 queries per connection, up to 20 connections ≈ 80 queries** (783–800). No pagination and no links to fuller lists.

### 2.2 Header card (16–94)
Cover section 220px (CSS 1697–1701): `user.profile_cover` else legacy `user.cover_image` else gradient placeholder (18–26) — **two overlapping cover fields exist on the model** (models.py:58 `cover_image`, models.py:70 `profile_cover upload_to='covers/'`). Username + category overlay bottom-left (29–32); hover-only edit-cover button (34–39, CSS opacity 0 until `.cover-image-section:hover` 1752–1774 — **undiscoverable on touch devices**). Avatar = signature image or initial with hover-only pencil (43–56, same touch problem, CSS 1823–1843); hard-coded always-green `online-status` dot (57, CSS 1850–1860) — **fake presence indicator, no real presence system**. Identity block: category badge, `email_verified` badge, member-since, 100-char bio preview (60–92).

### 2.3 Stats dashboard (97–180)
Six stat cards: Likes donnés, Cartes envoyées, Cartes reçues (+ unread sub-badge 133–135), Relations épistolaires, Cartes consultées, Suggestions. Icon tiles use **generic SaaS gradients — red/blue/green/purple/orange/cyan** (CSS 1962–1967) that clash with the sepia museum palette. Values have ids for AJAX refresh — but see the dead endpoint below.

### 2.4 Tabs (183–805, `switchProfileTab` 1034–1048)
Five tabs: Activité / Mes Likes / Mes Cartes / Relations / Paramètres. Same non-persistent class-toggle pattern as La Poste. On mobile ≤600px, tab labels vanish leaving icon-only buttons (CSS 3459–3461).

- **Activité (230–289):** icon-per-action activity feed (like/search/view/sent/received, 243–271) with `details` text + `timesince`. Switching to this tab calls `refreshStats()` (1045–1047).
- **Mes Likes (292–343):** grid of liked postcards (vignette, N°, title, like date); `is_animated_like` badge (317–323); click → `viewPostcard(id)` → `/parcourir/?highlight={id}` (1604–1606). Empty state links to browse.
- **Mes Cartes (346–463):** two sub-sections. Sent list: vignette, recipient or "Publication publique", 80-char message preview, date, and status badge Public / Lu / Non lu (390–398). Received list: unread highlight + "Nouveau" (423–438), sender signature-avatar, message preview, date; click → `viewReceivedPostcard(id)` which **ignores the id and just navigates to `/la-poste/`** (1608–1610) — no deep link to the specific card.
- **Relations (466–535):** connection cards with signature-avatar, username, category, sent/received counts, last exchange date (479–510); "Écrire" button → `sendCardTo(username)` → `/la-poste/?to=username` (1612–1614) — **dead handoff: neither the `la_poste` view (reads only `?postcard=`, views.py:1632) nor la_poste.html JS ever reads `to`**, so the user lands on La Poste with nothing prefilled and must reselect the recipient manually.
- **Paramètres (538–802):** six sections —
  1. **Bio** (541–571): click-to-edit display → textarea 500 chars with counter (1053–1069); save POSTs JSON `{bio}` to `/api/profile/update/` (1071–1095); server `update_profile` (views.py:887–927) accepts bio/country/city/website + privacy booleans `show_activity`/`show_connections`/`allow_messages` — **the UI only ever sends `bio`; the privacy toggles and location/website fields have no UI**.
  2. **Account info** (573–628): read-only email, join date, verified, last login.
  3. **Password change** (630–685, JS 1100–1188): 3 fields with eye-toggles, live strength meter (5-rule score, 1105–1127), match indicator, POST `/api/profile/change-password/` → `change_password` (views.py:1056–1082, keeps session via `update_session_auth_hash` 1077).
  4. **Signature** (688–722): preview + upload button → signature modal.
  5. **Permissions** (724–780): read-only granted/denied list for `can_view_rare`, `can_view_very_rare`, sending (always granted), staff.
  6. **Danger zone** (782–802): only a logout link — nothing dangerous (no account deletion/export).

### 2.5 Cover modal (809–891, JS 1193–1375)
Two sources: file upload (drag&drop, image-only, 5MB cap client 1302–1326 and server views.py:972–978) or "choose a postcard" — grid loaded from `/api/postcards/for-cover/` (`get_postcards_for_cover`, views.py:1139–1152: **50 random postcards** via `order_by('?')`, again unfindable/expensive; client search filters only by number, 1265–1273). Save POSTs FormData to `/api/profile/cover/` → `upload_cover` (views.py:959–1053): file path saves to `profile_cover`; URL path **server-side downloads the given `cover_url` with `requests.get(url, timeout=10)` (1002–1028) — an SSRF vector (arbitrary URL, no domain allowlist) and a media-architecture smell** (re-downloading its own hosted image over HTTP instead of copying the file). On success the page swaps the img with a `?timestamp` cache-buster (1354–1367).

### 2.6 Signature modal + drawing (893–990, JS 1380–1599)
Upload (2MB cap client 1434–1437 / server views.py:940–941) or **draw**: 400×200 canvas (963), 3 ink colors (sepia/amber/blue-black, 973–975), brush-size slider, mouse+touch drawing (1530–1554), clear; `canvas.toDataURL('image/png')` → back to the signature modal as preview (1590–1599); saved as blob `signature.png` via FormData to `/api/profile/signature/` → `upload_signature` (views.py:930–956, saves to `CustomUser.signature_image`). Page-side swap without reload (1476–1502). Note: drawn signatures get an **opaque `#f5f0e8` background** (1533–1534, 1578–1579) — not transparent — so they appear as a beige rectangle on the postcard compose/message views and as the avatar.

### 2.7 Broken stats refresh
`refreshStats()` fetches **`/api/profile/stats/` which is not routed anywhere** (profile.html:1004; core/urls.py:33–36 has only update/signature/cover/change-password). Called on every page load (1646–1649) and every switch to the Activité tab (1045–1047) → guaranteed 404 each time, silently swallowed (1026–1028).

---

## 3. Endpoint catalog (social features)

**Used by la_poste.html** (routes core/urls.py:41–49):
| Endpoint | Method | View | Template call site |
|---|---|---|---|
| `/api/users/search/?q=` | GET | `search_users` views.py:1892–1906 | la_poste.html:1023 |
| `/api/la-poste/send/` | POST JSON | `send_postcard` views.py:1676–1745 | la_poste.html:1069 |
| `/api/la-poste/<id>/message/` | GET (side-effect: marks read) | `get_postcard_message` views.py:1748–1779 | la_poste.html:1141 |
| `/api/la-poste/<id>/comment/` | POST JSON | `add_comment` views.py:1862–1889 | la_poste.html:1223 |

**Used by profile.html** (routes core/urls.py:33–36, 56):
| Endpoint | Method | View | Template call site |
|---|---|---|---|
| `/api/profile/stats/` | GET | **NO ROUTE — 404** | profile.html:1004 |
| `/api/profile/update/` | POST JSON | `update_profile` views.py:887–927 | profile.html:1075 |
| `/api/profile/change-password/` | POST JSON | `change_password` views.py:1056–1082 | profile.html:1163 |
| `/api/profile/cover/` | POST FormData | `upload_cover` views.py:959–1053 | profile.html:1341 |
| `/api/profile/signature/` | POST FormData | `upload_signature` views.py:930–956 | profile.html:1463 |
| `/api/postcards/for-cover/` | GET | `get_postcards_for_cover` views.py:1139–1152 | profile.html:1238 |

**Routed but never called from any template (dead API surface):** `/api/la-poste/postcards/` (`get_user_postcards` views.py:1791–1818), `/api/la-poste/public/` (`get_public_postcards` views.py:1821–1846), `/api/la-poste/<id>/read/` (`mark_postcard_read` views.py:1849–1859), `/api/la-poste/check-signature/` (`check_user_signature` views.py:1782–1788), plus `toggle_connection_favorite` / `update_connection_notes` (views.py:1085–1109).

**Routed views whose templates DO NOT EXIST → 500 TemplateDoesNotExist:** `profile_settings` renders `profile_settings.html` (views.py:836), `profile_connections` → `profile_connections.html` (860), `profile_favorites` → `profile_favorites.html` (871), `profile_activity` → `profile_activity.html` (882), `view_user_profile` → `view_profile.html` (1136). None of these five templates exist in `templates/` (glob confirmed). URLs are live at `/profil/parametres/`, `/profil/connexions/`, `/profil/favoris/`, `/profil/activite/`, `/utilisateur/<username>/` (core/urls.py:26–30). Consequently **there is no way to view another user's profile** — usernames on the wall/connections are plain text, not links, and the fallback page would crash anyway.

---

## 4. Migration-relevant notes (Render → OVH)
- All social imagery flows through model helpers: `SentPostcard.get_image_url/get_vignette_url/get_video_url` delegate to `Postcard.get_grande_url/get_vignette_url/get_animated_urls` (models.py:570–588) — the storage swap concentrates there.
- User-generated media: `signature_image` (models.py:52), legacy `cover_image` (58), `profile_cover upload_to='covers/'` (70) are local `ImageField`s served via `.url` — these must move to the new media store; the `?timestamp` cache-busters (profile.html:1359, 1481, 1494) suggest prior CDN/cache pain.
- `upload_cover`'s URL-download branch (views.py:1002–1043) does an HTTP round-trip to fetch the site's own postcard image; on OVH this should become a server-side file copy (and the SSRF hole closed).
- An `admin_sync_ovh.html` template already exists (templates/admin_sync_ovh.html), so OVH object storage work has begun elsewhere in the app.



## Issues (flat list)

- profile.html:1004 fetches /api/profile/stats/ which has no route in core/urls.py (33-36) — 404s on every profile load (1646-1649) and every Activité tab switch (1045-1047), silently swallowed; stat cards never refresh
- core/urls.py:26-30 routes profile_settings/profile_connections/profile_favorites/profile_activity/view_user_profile, but their templates (profile_settings.html, profile_connections.html, profile_favorites.html, profile_activity.html, view_profile.html) do not exist — all five URLs 500 with TemplateDoesNotExist; there is no working public-profile page at all
- profile.html:1612-1614 sendCardTo() navigates to /la-poste/?to=username but neither the la_poste view (views.py:1632 reads only ?postcard=) nor la_poste.html JS reads 'to' — the 'Écrire' button on connection cards silently drops the recipient
- views.py:1632-1638/1670 builds preselected_postcard from ?postcard= but la_poste.html never references it — card preselection from elsewhere in the site is dead
- la_poste.html:2308/2782/2817 use font-family 'Dancing Script' but the font is never loaded (base.html:7-8 has no font link; base.css has no @font-face) — the signature 'handwriting' look silently falls back to generic cursive/Georgia
- la_poste.html:1027-1032 and 1235-1242 build DOM via innerHTML template literals with unescaped user data (u.username, u.category, data.comment.message) — unsafe injection pattern (self-XSS today, stored XSS if this pattern is reused server-side)
- la_poste.html:1030 shows raw category slugs (e.g. 'subscribed_verified') in the recipient autocomplete because search_users (views.py:1904) returns .values('username','category') without get_category_display
- upload_cover (views.py:1002-1043) server-side downloads any client-supplied cover_url with requests.get — SSRF vector with no domain allowlist; also re-downloads the site's own media over HTTP instead of copying the file
- get_postcard_message (views.py:1758-1760) marks a card read as a side effect of a GET; the dedicated POST /api/la-poste/<id>/read/ endpoint (views.py:1849-1859) is never called by any template
- After reading a card, only the item badge is removed (la_poste.html:1174-1179); the header unread pill (28-36) and Reçues tab badge (85-87) stay stale until full reload; sending a card forces location.reload() (1090)
- Compose draft loss: Escape key (la_poste.html:1291-1299) or backdrop click (349) closes the compose modal with no confirmation, and resetComposeForm (808-846) wipes the draft
- Switching stamp 10c→5c silently truncates a typed message to 44 chars (la_poste.html:979-983) with no warning
- send_postcard (views.py:1689-1704) accepts any stamp_type string (only '5c' gets the 44 limit) and trusts client-supplied is_animated; no rate limiting; recipient gets no notification of a new card
- Picker inventory is a random subset: order_by('?')[:100] static / random 200→50 animated (views.py:1657-1660) and 50 random for covers (1142) — users cannot reliably find a specific card; ORDER BY RANDOM() is expensive; picker search (la_poste.html:911-921) only filters the loaded subset
- Wall template calls postcard.comments.count per post (la_poste.html:302) — ~50 COUNT queries per page despite prefetch_related; profile_view builds connections with ~4 queries per connection ×20 (views.py:783-800)
- add_comment (views.py:1862-1889) does not enforce the 500-char cap server-side (TextField max_length not validated on .create()); comment failures give the user no feedback (la_poste.html:1245-1247) and the comment-count button never updates
- Received/sent lightbox shows the vignette, not the large scan (viewPostcardImage reads the grid img src which is get_vignette_url — la_poste.html:124/191, 1118-1122)
- profile.html:1608-1610 viewReceivedPostcard(postcardId) ignores its argument and navigates to /la-poste/ — no deep link to the card, and la_poste has no mechanism to open a specific card either
- Two overlapping cover-image fields on CustomUser (models.py:58 cover_image, models.py:70 profile_cover) with template fallback logic (profile.html:18-21)
- Fake presence: .online-status dot is hard-coded always green (profile.html:57, CSS 1850-1860)
- update_profile (views.py:902-916) supports country/city/website and privacy booleans show_activity/show_connections/allow_messages, but no UI exists for any of them — settings tab only edits bio
- Drawn signatures are exported with an opaque #f5f0e8 background (profile.html:1533-1534, 1578-1579) instead of transparency, so they render as beige rectangles on postcards and avatars
- Edit affordances (cover camera btn profile.html:34-39/CSS 1752-1774, avatar pencil 50-55/CSS 1823-1843) are opacity-0 until hover — invisible on touch devices
- Tab state is non-persistent class toggling in both pages (la_poste.html:779-788, profile.html:1034-1048) — no URL hash/history, reload always returns to the first tab; no pagination anywhere (30/30/50 caps in views.py:1640-1650, 10/10/20/15 caps in 768-803) and no links to fuller lists
- Design-system debt: ~1,700 lines of inline CSS in la_poste.html (1314-3008) and ~1,860 in profile.html (1652-3511) with duplicated modal/notification/scrollbar code and hard-coded hex palette; stat icons use off-brand SaaS gradients (red/blue/purple/cyan, profile.html CSS 1962-1967); 25 floating emoji + 60 dust particles animate permanently (la_poste.html:736-774); no prefers-reduced-motion handling
- Accessibility: tabs lack role=tablist/aria-selected, modals lack role=dialog/aria-modal/focus traps, everything is inline onclick, keyboard access to card actions is minimal; single 768px breakpoint on la_poste (2944-2988) and the %-positioned compose textarea (CSS 2298-2312) is cramped and fixed at 14px on mobile
- Dead API surface: /api/la-poste/postcards/, /api/la-poste/public/, /api/la-poste/<id>/read/, /api/la-poste/check-signature/, toggle_connection_favorite, update_connection_notes (views.py:1782-1859, 1085-1109) are routed but never called


## Quick wins

- Add the missing /api/profile/stats/ route (or delete refreshStats) — one urls.py line + a ~15-line JSON view reusing profile_view's counts kills a guaranteed 404 on every profile visit
- Wire the ?to= param: in la_poste.html read URLSearchParams on DOMContentLoaded, open compose at step 3 with the recipient prefilled — makes the Relations 'Écrire' button actually work
- Load 'Dancing Script' (or a self-hosted equivalent like Parisienne/Homemade Apple) in base.html — instantly restores the intended handwritten-postcard look on compose and message views
- Map category slugs to display labels in search_users (annotate get_category_display or a dict lookup) so the recipient autocomplete stops leaking internal codes
- Decrement the header/tab unread badges in viewPostcardMessage's success handler (elements already have stable ids/classes) and update the sent grid locally instead of location.reload() after sending
- Use textContent / createElement instead of innerHTML for comment append and user suggestions (la_poste.html:1027-1032, 1235-1242) — removes the injection pattern in ~10 lines
- Replace order_by('?') picker queries with order_by('number') + server-side search endpoint, so senders can find a specific card; same for the cover picker
- Show the large scan in the lightbox by passing get_image_url via a data attribute on .postcard-item instead of reading the vignette img src
- Annotate comment counts (Count('comments')) in the la_poste view and use the annotation in the template — removes ~50 queries per wall load
- Guard modal dismissal: confirm before closing compose when message/card selection is non-empty (single beforeClose check in closeComposeModal)
- Export drawn signatures with a transparent background (skip the fillRect, or composite-out #f5f0e8) so signatures sit naturally on the postcard art
- Remove or unroute the five template-less profile sub-pages (or point them at the tabbed profile) to stop live 500s at /profil/parametres/, /profil/connexions/, /profil/favoris/, /profil/activite/, /utilisateur/<u>/
- Make edit-cover/avatar buttons visible by default on coarse pointers (@media (pointer:coarse){ .edit-cover-btn,.avatar-edit-btn{opacity:1} })
- Restrict upload_cover's URL branch to same-host/media-host URLs (or replace with a postcard_id parameter and server-side file copy) — closes the SSRF and simplifies the OVH media migration