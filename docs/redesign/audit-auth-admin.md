# Audit — Auth pages & Custom Admin Dashboard ("Le Postier")

All paths relative to `C:/Users/mathe/Documents/CODING/Empire/le-postier/`.

## 1. Registration flow UX (register → 6-digit code → set password → complete)

### Backend flow (core/views.py, core/forms.py, core/urls.py)
- Routes (core/urls.py:16-22): `/inscription/` → `register`, `/verification/` → `verify_email`, `/verification/renvoyer/` → `resend_verification_code`, `/definir-mot-de-passe/` → `set_password`, `/inscription-terminee/` → `registration_complete`, `/connexion/` → `login_view`.
- **Step 1** `register` (core/views.py:549-569): username + email only via `SimpleRegistrationForm` (core/forms.py:23-71). Saves user with **unusable password**, `category='subscribed_unverified'`, generates a code, stores `pending_verification_user_id` in session, redirects to verify. If the verification email fails to send, it *still* redirects with no user-visible message (views.py:562-565 — the comment says "show a message" but none is set).
- **Step 2** `verify_email` (views.py:572-615): session-gated (redirects to register if no pending id); checks `user.verification_code == code` plus 30-min validity (views.py:594); on success sets `email_verified`, `category='subscribed_verified'`, clears code. Distinct French errors: "Ce code a expiré…" vs "Code incorrect…" (views.py:604-607). `resend_verification_code` (views.py:618-636) is a JSON endpoint (400 session expired / 404 / 500).
- **Step 3** `set_password` (views.py:639-678): gated on `email_verified`; uses `SetPasswordForm` (forms.py:95-128) which runs Django's `validate_password` (forms.py:113-119); on success **auto-logs the user in** (views.py:668) and redirects to complete.
- **Step 4** `registration_complete` (views.py:681-685): requires authentication.
- Smart recovery: `login_view` (views.py:688-720) detects a half-registered user (password never set) and re-enters the funnel at the correct step (views.py:701-706). Side effects: username-existence oracle, and `next` from GET is redirected to without validation (views.py:715-716 — open-redirect risk).
- Email sending `send_verification_email` (views.py:139+): HTML via `emails/verification_code.html` + plain-text alternative (views.py:150-161), subject "Vérification de votre compte - Collection Samathey" (views.py:143), plus an admin-notification email (views.py:176+).

### templates/login.html (176 lines)
- Extends base.html; **all styles inline in a `<style>` tag inside the content block** (lines 55-175), not in `{% block extra_css %}`.
- Look: full-viewport dark-brown gradient `#1a1208 → #0d0906` (line 62), 420px glass card, 24px radius, amber border glow (65-74). Amber palette `#b5600b/#d1872c/#ffc168` hardcoded throughout.
- Hand-written inputs (no Django form), correct `autocomplete` attrs (30, 40). Error shown via `{% if error %}` alert (15-19), single string from views.py:718.
- Hover: `translateY(-3px)` + glow on button (150-153).
- **No "forgot password" link** (footer 49-51 only links to register) — and no password-reset flow exists anywhere in core/urls.py.
- Uses `{% block page_title %}` (line 5) — see the dead-block finding below.

### templates/register.html (140 lines)
- The **odd one out visually**: gray card `rgba(32,32,32,…)` (line 10) instead of the brown glass used everywhere else; **light input fields** `rgba(255,255,255,0.95)` with dark text (39) vs dark inputs on every other auth page; pill button `border-radius:25px` (57) vs 12px elsewhere; `margin: 100px auto` (8) instead of the full-viewport flex-centering used by login/verify/set_password.
- Styles correctly placed in `{% block extra_css %}` (4-101) — the only auth page that does this.
- The only auth page rendering Django form widgets (`{{ form.username }}` line 124, `{{ form.email }}` line 129; widget attrs at forms.py:26-39).
- Errors: all field errors flattened into bare `<li>` elements **without a parent `<ul>`** (invalid HTML) and without field labels (110-118). French validation: unique email (forms.py:45-49), unique username + min 3 chars (forms.py:51-57).
- Input focus does `transform: scale(1.02)` (48) — layout jiggle.
- **No progress-step indicator**, even though steps 2 and 3 display a 3-step tracker whose step 1 is "Inscription".

### templates/verify_email.html (563 lines)
- 3-step progress tracker (10-29): Inscription ✓ → Vérification (active) → Mot de passe. Completed steps use green `#22c55e` gradient (283-287) — green is foreign to the amber palette.
- 6-digit segmented input, 3+3 with a dash separator (60-68), synced to hidden `code` field (69). JS (106-236): digit-only filter, auto-advance, backspace navigation, **full 6-digit paste support** (141-157), submit disabled until 6 digits (160-167). Good interaction quality.
- **Missing `autocomplete="one-time-code"`** on the visible digit inputs (61-67) — the Django widget has it (forms.py:84) but the template hand-builds the inputs, so mobile OTP autofill won't trigger.
- Resend: fetch POST with CSRF header (177-198), 60s countdown swap (200-217), toast notifications appended to `<body>` (219-230, slideIn animation 541-544).
- Server error rendered in `.error-message` with icon (44-53). Help text "check spam" (94-101).
- ~330 lines of inline CSS (238-562); responsive tweak at 480px (547-561).

### templates/set_password.html (606 lines)
- Progress tracker duplicated verbatim from verify_email (10-33; CSS comment "Same as verify_email" line 296) — pure copy-paste, no shared partial.
- Show/hide password toggles with dual eye SVGs on both fields (83-92, 146-155). Note: the second field's "eye-closed" SVG (151-154) is missing path segments present in the first (88-91) — visually inconsistent icon.
- Live strength meter: 4-requirement checklist (8 chars/upper/lower/digit, 104-129), 5-point score with special-char bonus (200-229), color-coded bar `weak/fair/good/strong` (502-505), French labels Faible/Passable/Bon/Excellent (238-250).
- **Match-indicator bug** (257-278): on mismatch the element's innerHTML is replaced with the X-icon + "ne correspondent pas" text (267-273); when passwords later match, only classes are toggled — the wrong text stays, now rendered green.
- Client checklist is cosmetic (submit never gated, 165) and **diverges from the server rules**: server runs Django `validate_password` (forms.py:113-119) which doesn't require upper/lower/digit but does check similarity/common passwords — mismatched expectations.
- Server errors: non_field + all field errors concatenated into one unlabeled box (50-66).

### templates/registration_complete.html (280 lines)
- Animated success: scaleIn circle + stroke-dashoffset checkmark draw (104-131), 6-span CSS confetti (134-163), `🎉` emoji in the h1 (22).
- 3 action cards → browse / profile / animated_gallery (33-62) + home CTA (64-69). Mobile: cards become horizontal rows (260-278).

### templates/emails/verification_code.html (73 lines)
- Table-based layout (correct for email), fully inline styles, Georgia serif, paper `#f5f0e8` background (8-9).
- Header uses CSS `linear-gradient` with **no `bgcolor` fallback** (16) — Outlook will drop the amber header background.
- Code: 42px Courier, 8px letter-spacing (42-44); 30-min expiry note (47-49).
- Branding inconsistency: header says "📮 Le Postier" (17-19), backend emails say "Collection Samathey" (views.py:143,151-161); footer hardcodes "© 2025" (62-64).

## 2. Admin dashboard — templates/admin_dashboard.html (1977 lines)

Single monolithic page (no SPA), server-rendered context + fetch-based modals. Access: `@user_passes_test(is_admin)` (core/views.py:1913-1914); route `/tableau-de-bord/` (urls.py:59).

### Section structure (top to bottom)
1. **Header** (10-95): title + username + date; actions: "Nouvelle Carte" modal trigger (23), **Export dropdown** — 5 CSV links `/api/admin/export/?type=sessions|pageviews|likes|searches|users` (40-77), refresh = `location.reload()` (80), gear link to Django `/admin/` (88).
2. **Real-time** (98-143): "EN DIRECT" pulse dot, live clock, active-visitor count, per-visitor cards (flag/country/city/current page/device/browser/username), click → IP lookup modal. Server seeds initial list; JS re-polls.
3. **Quick stats grid** (146-316): 8 cards — Utilisateurs, Vues aujourd'hui, Sessions, Likes, Cartes postales, Recherches, Messages (unread alert badge 283-292), Suggestions (pending badge 303-311); day-over-day growth % coloring.
4. **Performance metrics** (319-386): bounce rate with high/medium/low thresholds at 70/50 (335), avg session duration, pages/session, week-over-week growth.
5. **Charts** (389-496): 4 `<canvas>` charts (see below). Legends are hand-built HTML with inline `style="background: #hex"` dots (429-443, 462-473).
6. **Geography** (499-601): top countries (clickable → country modal, `widthratio` bars 519), top cities, ISPs with VPN/proxy warning (557-566), traffic sources direct/referral + top referrers.
7. **Search analytics** (604-670): all-time top, today, zero-result searches (with 🎉 empty-state 665).
8. **Tabs** (673-1036) — 6 tabs, pure class-toggle JS (1280-1290):
   - *Likes* (726-786): table with postcard link, animated/static badge, user, geo, device, IP-lookup button.
   - *Utilisateurs* (789-857): table with avatar initial, inline `<select>` category editor → PUT, delete button (hidden for superusers, 843) → DELETE.
   - *Cartes* (860-909): top-viewed / top-liked mini cards, rarity stats grid (common/rare/very_rare).
   - *Messages* (911-934): contact messages w/ unread state and IP.
   - *Suggestions* (937-965): animation suggestions with status `<select>` → PUT.
   - *IPs* (967-1035): most-active IP table + "IPs suspectes" list.
9. **System health** (1039-1104): media storage card (vignette/grande/animated counts from `media_stats` — relevant to the OVH media migration), database card, themes count.
10. **Modals** (1107-1259): Add Postcard (form: number/title/description/keywords/rarity), IP Lookup, User Analytics, Country Analytics, Postcard Analytics — the last four are skeletons filled by fetch + template-literal `innerHTML`.
11. **Inline JS** (1264-1975, ~700 lines): clock, tabs, export menu, modal CRUD, real-time polling, notifications, ESC-closes-all (1826-1834), Chart.js init (1837-1974).
12. **CSS link at line 1977** — the dashboard stylesheet is loaded at the *bottom of the body*, after all content (FOUC on every load; should be in `{% block extra_css %}`).

### Chart libraries / CDNs
- **Chart.js, unpinned, from CDN**: `https://cdn.jsdelivr.net/npm/chart.js` (1262) — no version, no SRI, no self-hosting (breaks the self-sufficiency goal of the OVH migration; also always-latest = future breakage risk).
- Google Analytics gtag `G-YZX5PNSJZG` inherited from base.html (base.html:13-19).
- Charts: `activityChart` line chart, 30-day views/sessions/likes, amber/green/red (1841-1887); `usersChart` doughnut by category, 65% cutout (1892-1913); `devicesChart` doughnut (1918-1938); `hourlyChart` bar (1943-1973). Data injected via `{{ daily_stats|safe }}` / `{{ hourly_traffic|safe }}` (1266-1267) and raw template values inside JS (1898-1902, 1924-1927).

### /api/admin/* endpoints actually called by the template
| Endpoint | Method | Call site |
|---|---|---|
| `/api/admin/export/?type=…&period=…` | GET (links) | 40-77 |
| `/api/admin/add-postcard/` | POST | 1328 |
| `/api/admin/user/<id>/` | PUT / DELETE | 1353 / 1376 |
| `/api/admin/suggestion/<id>/` | PUT | 1395 |
| `/api/admin/ip/<ip>/` | GET | 1422 |
| `/api/admin/user-analytics/<id>/` | GET | 1513 |
| `/api/admin/country-analytics/<country>/` | GET | 1598 |
| `/api/admin/postcard-analytics/<id>/` | GET | 1686 |
| `/api/admin/realtime/` | GET, polled every 30s | 1772, 1809 |

Registered but **never called** by the template (dead surface, urls.py:60-79): `/api/admin/stats/`, `users/`, `postcards/`, `postcard/<id>/`, `suggestions/`, `postcards/next-number/`, `geographic/`, `upload-media/`, `media-stats/`, `likes/`, `detailed-stats/`. urls.py also has **duplicate registrations**: `geographic` (69 & 75), `ip` (70 & 76), and `/api/admin/export/` mapped to two *different* views (71 `admin_export_data`, 82 `admin_export_analytics` — line 82 can never match).

### static/css/admin_dashboard.css (2502 lines)
- 20 labeled sections: Header (14), Section titles (167), Real-time (187), Stats (395), Metrics (595), Charts (676), Geographic (780), Search (935), Tabs (1024), Tables (1149), Badges (1295), Postcards preview (1401), Messages & suggestions (1526), IPs (1620), System (1687), Modals (1776), Loading & notifications (2220), Responsive (2295), Print (2472).
- **Zero CSS custom properties** (`var(--…)` count = 0); ~25 distinct hardcoded hex colors. Amber brand (`#b5600b`×15, `#ffc168`×25, `#d1872c`) plus a Tailwind-default accent rainbow per stat icon: blue `#60a5fa`, yellow `#fbbf24`, green `#4ade80`, red `#f87171`, purple `#c084fc`, cyan `#22d3ee`, orange `#fb923c` (468-490) — this rainbow is what most undermines a "museum-quality" feel.
- Typeface: `font-family: inherit` everywhere → the dashboard renders in the site's serif **"Bookman Old Style", Georgia** (static/css/base.css:7) — a serif analytics dashboard, with `'Courier New'` for IPs/codes (245, 1616, 1674, 2026).
- Idiom: dark glassmorphism — layered `linear-gradient` cards, 14-24px radii, `translateY` hovers, heavy box-shadows (e.g. 16-29, 117-138). Notably clean specificity: only 2 `!important` outside print; print styles nuke color (2500-2502).
- Responsive: 1400/1200/992/768/480 breakpoints (2297-2469); tables scroll horizontally (2376-2380); tab nav stacks vertically on mobile (2363-2370); header buttons collapse to icon-only (2411-2417).

### Restyle vs rebuild verdict
- **Auth pages: restyle, cheap.** Five self-contained pages, ~1,600 lines of per-page inline CSS that is 60-80% duplicated (progress steps, cards, buttons, error boxes, notifications). Consolidate into one `auth.css` + shared progress-steps/notification partials; keep the JS (code input, strength meter, toggles — the interaction quality is already good), fix the two JS bugs, and bring register.html into the funnel's visual language. No structural rework needed.
- **Admin dashboard: moderate rebuild of the shell, not a full rewrite.** The HTML structure is semantic and section-ordered, so ~80% of a visual overhaul is achievable purely in admin_dashboard.css by introducing design tokens and replacing the accent rainbow. What forces surgery beyond CSS: (a) ~700 lines of inline JS incl. unescaped `innerHTML` interpolation of user-controlled data (usernames, search keywords, page titles at 1425-1495, 1516-1582, 1779-1801 — stored-XSS-into-admin risk) that should move to a static module with escaping; (b) hardcoded legend/dot colors in the HTML (429-443, 462-473) and chart colors in JS that must follow the new palette; (c) Chart.js must be pinned and self-hosted for the OVH VPS; (d) the stylesheet link must move from body-bottom (1977) to the head. Estimate: CSS re-skin + JS extraction ≈ 2-3 focused days; full framework rebuild is not justified.

## 3. templates/admin_sync_ovh.html (42 lines)
**Dead placeholder.** Byte-identical to `templates/base.html` (verified with `diff`): bare skeleton with navbar include (22), messages block (24-32), *empty* `{% block content %}` (34), footer "- A Z DATA Production 2025 -" (37), GA snippet (13-19). No URL pattern, view, or any other file references `sync_ovh` anywhere in the project (grep: zero matches outside .venv). The OVH media-sync admin page was scaffolded and never built — for the OVH migration this page needs to be designed and wired from scratch (a natural home for it: the "Stockage média" system card at admin_dashboard.html:1049-1064 and the unused `/api/admin/upload-media/` + `/api/admin/media-stats/` endpoints, urls.py:72-73).

## 4. Cross-cutting template-inheritance defect
`templates/base.html:10` defines `{% block title %}`, but **16 templates define `{% block page_title %}`** (login.html:5, register.html:103, verify_email.html:4, set_password.html:4, registration_complete.html:4, admin_dashboard.html:5, +10 more). The block never renders — every page's browser tab reads "Collection Samathey". One-line fix in base.html.


## Issues (flat list)

- Dead title block: base.html:10 defines 'title' but 16 templates (login.html:5, register.html:103, verify_email.html:4, set_password.html:4, registration_complete.html:4, admin_dashboard.html:5, ...) define 'page_title' — browser tab title never changes site-wide
- admin_sync_ovh.html is byte-identical to base.html with an empty content block, and no URL/view references it — the OVH sync page does not exist
- admin_dashboard.html:1262 loads Chart.js from CDN unpinned (no version, no SRI, not self-hosted) — breakage risk and contradicts OVH self-hosting goal
- admin_dashboard.html:1977 loads admin_dashboard.css at the bottom of the body content block — guaranteed FOUC on every dashboard load
- XSS risk in dashboard modals: user-controlled data (usernames, search keywords, page titles, ISP strings) interpolated unescaped into innerHTML template literals (admin_dashboard.html:1425-1495, 1516-1582, 1634-1664, 1749-1756, 1779-1801) — stored XSS executing in an admin session
- core/urls.py duplicate routes: geographic (69 & 75), ip lookup (70 & 76), and /api/admin/export/ bound to two different views (71 admin_export_data vs 82 admin_export_analytics — line 82 unreachable)
- 11 registered /api/admin/* endpoints are never called by the dashboard template (stats/, users/, postcards/, postcard/<id>/, suggestions/, next-number/, geographic/, upload-media/, media-stats/, likes/, detailed-stats/ — urls.py:60-79): dead attack/maintenance surface
- register.html breaks the funnel's visual language: gray card (line 10), light inputs (39), pill button (57), margin-centering (8), and no progress-step indicator, while steps 2-3 share a dark amber design with a 3-step tracker
- set_password.html:257-278 match-indicator bug: after a mismatch rewrites innerHTML, a subsequent match only toggles classes — 'Les mots de passe ne correspondent pas' stays displayed in green
- verify_email.html:61-67 hand-built code inputs lack autocomplete="one-time-code" (the unused Django widget at forms.py:84 has it) — mobile OTP autofill broken
- Client password checklist (set_password.html:200-229: upper/lower/digit required) diverges from server rules (forms.py:113-119 Django validate_password: similarity/common-password checks, no character-class rules) — users can satisfy one and fail the other
- login.html:49-51 has no 'forgot password' link and no password-reset flow exists anywhere in core/urls.py
- views.py:562-565 register(): if the verification email fails to send, user is redirected to the code-entry page with no message — dead-ends users who never got a code
- views.py:715-716 login_view redirects to raw ?next= without url_has_allowed_host_and_scheme validation — open redirect; also views.py:701-706 leaks username existence via differing redirect behavior
- admin_dashboard.css has zero CSS custom properties and ~25 hardcoded hex colors including a Tailwind-default accent rainbow on stat icons (468-490) that clashes with the amber brand and the museum ambition
- Dashboard typography: font-family inherit picks up 'Bookman Old Style' serif (base.css:7) for a data dashboard; chart/legend colors triple-defined (CSS, inline HTML style attrs at admin_dashboard.html:429-443/462-473, and JS at 1849-1953)
- ~1,600 lines of duplicated inline CSS across the 5 auth templates (progress steps duplicated verbatim between verify_email.html:253-357 and set_password.html:296-357; toast notification component duplicated verify_email.html:219-230 and admin_dashboard.html:1812-1823)
- register.html:110-118 renders <li> error items without a parent <ul> (invalid HTML) and drops field names; set_password.html:50-66 concatenates all errors into one unlabeled box
- emails/verification_code.html:16 header uses CSS linear-gradient with no bgcolor fallback (blank header in Outlook); branding split between 'Le Postier' (email header line 17) and 'Collection Samathey' (subject/plain-text views.py:143-161); hardcoded '© 2025' (line 62)
- set_password.html:151-154 second eye-closed SVG icon is missing path segments present in the first field's icon (83-92) — visibly different icons for the same action
- register.html:48 input focus applies transform: scale(1.02) causing layout jiggle
- Dashboard refresh button is location.reload() (admin_dashboard.html:80) and realtime polling is fixed 30s innerHTML rewrite (1809) — no partial updates, no backoff, no visibility-change pause


## Quick wins

- Rename {% block title %} to also render page_title in base.html:10 (one line) — restores correct browser-tab titles on 16 pages instantly
- Move the stylesheet link at admin_dashboard.html:1977 into {% block extra_css %} — kills dashboard FOUC
- Pin and self-host Chart.js (replace admin_dashboard.html:1262) — required for the OVH VPS anyway; do it now to freeze the API version
- Add autofocus + autocomplete="one-time-code" to the first digit input at verify_email.html:61 — enables mobile OTP autofill
- Fix the set_password.html:257-278 match-indicator by restoring the innerHTML in the match branch (5 lines)
- Delete the duplicate/unreachable routes at core/urls.py:75, 76, 82
- Delete admin_sync_ovh.html or turn it into the real OVH sync page — its natural backend already exists as unused /api/admin/upload-media/ and /api/admin/media-stats/ (urls.py:72-73)
- Add a 'Mot de passe oublié ?' link target and wire Django's built-in password-reset views — the email infrastructure (send_verification_email pattern, views.py:139) already exists
- Extract the 3-step progress tracker into a shared partial (currently duplicated verbatim in verify_email.html and set_password.html) and include it on register.html so step 1 matches the funnel
- Define ~10 CSS custom properties (brand amber, surfaces, borders, semantic accents) at the top of admin_dashboard.css and search-replace the 25 hardcoded hexes — 80% of the dashboard re-skin with zero HTML changes
- Replace the stat-icon Tailwind rainbow (admin_dashboard.css:468-490) with a restrained 2-3 tone amber/ink scheme — single biggest step toward the museum feel
- Set a message via django.contrib.messages when verification email send fails at views.py:562-565 (the messages container already exists in base.html:24-32)