# Le Postier — Backend Performance + Deployment/Storage Audit
Project root: `C:/Users/mathe/Documents/CODING/Empire/le-postier` (Django 4.2.7, ~1,860–1,960 postcards per the two committed CSVs: `db_cp_16_02_2024.csv` = 1,862 rows, `export-251221_db.csv` = 1,964 rows). Read-only audit; nothing was modified.

---

## 1. Media/storage architecture — per-request filesystem scanning

### 1.1 The primitives and their cost

**`Postcard._find_local_image(folder)`** — `core/models.py:225-252`
- 1 `base_path.exists()` stat, then probes 8 extensions (`.jpg .jpeg .png .gif` + uppercase) for the zero-padded number (models.py:241-244), then 8 more for the raw number (models.py:246-250).
- Cost: **2 stat() syscalls best case** (dir exists + first `.jpg` hit), **17 worst case** (miss, or file named with uppercase ext / unpadded number).
- Called by `get_vignette_url` (254), `get_grande_url` (257, falls back to vignette → doubles cost on miss), `get_dos_url` (261), `get_zoom_url` (264, falls back to grande → can chain 3 lookups).

**`Postcard.get_animated_urls()`** — `core/models.py:268-297`
- 1 dir-exists stat + 4 single-file probes (280-284) + a multi-file loop that always probes i=0 AND i=1 even when nothing exists (the `if not found and i > 0` break at 294 never fires for i=0).
- Cost: **13 stat() calls for a card with no animation** (the common case), ~10-14 with one video, up to 4+4×k for k videos.
- `has_animation()` (models.py:308), `check_has_animation()` (302), `get_first_video_url()` (311), `video_count()` (315) each re-run the full scan — no memoization whatsoever, not even per-instance.

**`SentPostcard.get_image_url()/get_vignette_url()/get_video_url()`** — `core/models.py:570-588` — delegate to the same scanners, so every social-wall JSON row also stats the disk.

**There is no `has_animation` DB field.** `has_images` is the only persisted flag (models.py:194); `update_image_flags()` (models.py:318-320) saves only that. `scan_media.py:149-152` even guards `hasattr(postcard, 'has_animation')` for a field that doesn't exist. This absence is the root cause of all per-request animation scanning.

### 1.2 Per-page cost quantified

**Browse `/parcourir/` — the worst offender.** `core.views.browse` (views.py:1234-1297) loads **ALL** `has_images=True` cards with **no server-side pagination** (`postcards_list = list(postcards)`, views.py:1263; pagination is client-side only, `ITEMS_PER_PAGE = 50` in JS, browse.html:611). The template then calls, **per card**:
- `get_vignette_url` ×3 (browse.html:364, 373, 626)
- `get_grande_url` ×2 (365, 623), `get_dos_url` ×2 (366, 624), `get_zoom_url` ×2 (367, 625)
- `get_animated_urls` ×4 (368, 393, 427, 628) + `get_first_video_url` ×2 (369, 629 — each is another full scan)

= 9 image lookups + 6 animation scans per card ≈ **96 stat() calls/card best case, ~231 worst case**. For ~1,900 cards that is **≈180,000–440,000 filesystem stat() syscalls per single anonymous page view**, plus the entire catalogue serialized TWICE into the HTML (card grid at browse.html:358-441 and a second full inline-JS copy `allPostcardsData` at browse.html:616-632) → multi-MB response rendered by a sync gunicorn worker.

**Other views:**
- `home` (views.py:1205-1227): 30 random cards (`order_by('?')`, 1214) × `get_animated_urls` ≈ **390 stats/view**, on the busiest page of the site.
- `animated_gallery` (views.py:1300-1339): iterates **every** `Postcard.objects.all()` (1303) calling `get_animated_urls` (1307) until 100 hits → worst case ≈ **25,000 stats/request**. Also shadows the model method: `postcard.video_count = len(video_urls)` (1309).
- `la_poste` (views.py:1626-1673): two `order_by('?')` pulls (1657, 1659), then `p.has_animation()` on 200 cards (1660) = **2,600 stats**, plus ≥210 more `get_vignette_url` calls in la_poste.html:124, 191, 279, 604-620.
- `get_postcard_detail` API (views.py:1483-1498): 5 image lookups + animated scan ≈ 25-90 stats per click; also `get_postcards_for_cover` (views.py:1142-1150) — 50 random cards × 3 lookups each, with the filter `if p.get_vignette_url()` re-scanning (1150).
- `admin_dashboard` (views.py:1968-1971): `has_animation()` on 500 cards = **6,500 stats**, plus `glob('*.*')` directory listings of Vignette/Grande/animated (2330-2335). `admin_media_stats` (2960-2996) does a full `os.walk` size computation per call.
- **Django admin postcard list**: `PostcardAdmin.list_display` includes `has_images` which is overridden by the method at `core/admin.py:90-93` calling `check_has_vignette()` → disk scan per row per admin page.
- `admin_postcard_detail` GET (views.py:2802-2823) and `debug_postcard_images` (3003-3027): full scans per call.
- Templates `profile.html:304, 361, 425` and `animated_gallery.html:76-115` (`get_grande_url`, `get_vignette_url`, `get_first_video_url` ×2, `video_count` ×2 → 2 more full animation scans per card ×100 cards).

### 1.3 MediaServeMiddleware — Python serving every media byte

`core/middleware.py:25-147`, wired **last** in MIDDLEWARE (`settings.py:42`), so every image/video request first traverses Security, WhiteNoise, Session, Common, CSRF, Auth, Messages, XFrameOptions middleware (session DB lookups per image). It then:
- stats the file (middleware.py:64); on miss runs `find_file_case_insensitive` (102-147) which **`iterdir()`s the whole directory** (~2,000 entries) per path segment and probes 12 extensions — a directory listing per 404.
- serves via `FileResponse` with only `Cache-Control: public, max-age=86400` (90) — no ETag/Last-Modified/immutable, no conditional-GET support, `Content-Disposition` set needlessly (93).
- Through **gunicorn with 2 sync workers, 120s timeout** (`start.sh:63`, `Dockerfile` CMD): a browse page triggering ~50 lazy-loaded vignettes queues 50 Python requests through 2 workers; any mp4 stream pins a worker.

### 1.4 Reusable tooling that already exists (management commands)

Full inventory (36 commands, many overlapping):
- **`update_flags.py` (209 lines) — the keeper.** Builds in-memory directory indexes once (`build_index`, update_flags.py:74-96, maps padded+unpadded stems → files) then bulk_updates `has_images` (189). Already counts animations (157-165) but cannot persist them (no field). This is the exact pattern the caching refactor needs — extend it to persist per-card media paths/animation counts.
- `update_postcard_flags.py` (26 lines) — naive per-card `update_image_flags()` loop = N×17 stats + N saves; superseded by update_flags; but it's the one wired to the admin button (`core/admin.py:83`) and `migrate_ovh_to_render` — retire it.
- `scan_media.py` (222 lines) — reports media stats and can auto-create DB entries from files (scan_media.py:110-167); reusable for VPS post-rsync verification.
- `import_csv.py` (251 lines) — robust CSV import (multi-encoding, delimiter autodetect, column-name mapping, `--update`, `--dry-run`); the canonical importer. Duplicated by `import_csv_flexible.py` (361), `import_csv_update.py` (262, ALSO duplicated as stray app-level module `core/import_csv_update.py`), `import_postcards_csv.py` (219), `import_data_complete.py` (405), `import_sql_data.py` (302), `import_mysql_dump.py` (384), `import_from_sql.py` (91) — 8 importers to collapse to 1.
- `create_admin.py` (33 lines) — **hardcodes superuser credentials `samathey` / `<mot-de-passe-redacte>` in the repo and prints them** (create_admin.py:10-12, 33-34); `build.sh` runs it every deploy, resetting the password.
- FTP-era commands, obsolete once media lives on the VPS: `sync_from_ovh.py` (298 — pulls FROM OVH FTP to Render disk), `migrate_from_ovh.py` (378), `import_from_ftp.py` (310), `sync_images_from_ftp.py` (165), `quick_sync.py` (36), `render_setup.py` (101), `complete_setup.py` (171), `full_setup.py` (156), `upload_media.py` (167).
- Diagnostics: `check_media.py` (182), `diagnose_media.py` (98), `full_media_diagnostic.py` (179), `check_keywords.py` (37).
- Misc: `export_to_csv.py`/`generate_csv_export.py` (dupes), `update_keywords.py`, `fix_postcard_order.py`, `create_postcards_from_images.py`, `populate_from_images.py`, `quick_populate.py`, `populate_test_data.py` (**0 bytes**).
- Junk: `__init__ - Copie (3).py`, `__init__ - Copie (4).py` (Windows copy artifacts inside the commands package).

---

## 2. Render-specific code to remove (complete grep of `RENDER` / `/var/data` / `onrender.com`)

| File | Lines | What |
|---|---|---|
| `manage.py` | 9-13 | **Switches to `settings_production` when RENDER set** — split-brain: gunicorn (wsgi.py:13) always uses `settings`, so management commands on Render ran under a DIFFERENT config (no MediaServeMiddleware, `MEDIA_ROOT=BASE_DIR/media`, no CSRF origins) |
| `le_postier/settings.py` | 106-126 | `IS_RENDER`/`PERSISTENT_DISK_EXISTS` probe, `/var/data/media` MEDIA_ROOT, debug `print()`s |
| `le_postier/settings.py` | 143-148 | `https://*.onrender.com` in CSRF_TRUSTED_ORIGINS |
| `le_postier/settings_production.py` | whole file | Render-era duplicate settings (`.onrender.com` at :13, hardcoded SECRET_KEY at :8, conflicting MEDIA_ROOT at :108, LOGIN_URL name mismatch :113) — delete |
| `start.sh` | whole file | Render startup (RENDER echo :9, /var/data probing :13-32, gunicorn `$PORT` :63) |
| `build.sh` | whole file | Render build hook (runs `create_admin` every deploy :24) |
| `fix_deployment.sh`, `sync_images.sh`, `simple_app.py` | whole files | One-off Render debugging artifacts (simple_app.py:12 repeats the real SECRET_KEY) |
| `Dockerfile` | :7 `PORT=10000`, :29-31 | Runs `collectstatic`/`migrate --run-syncdb` at **build** time with `|| true` masking failures |
| `runtime.txt` | whole file | Render Python pin |
| `core/models.py` | 13-21 | `get_media_root()` copy #1 |
| `core/middleware.py` | 18-22, 25-30 | `get_media_root()` copy #2 + Render-rationale docstring |
| `core/views.py` | 3063-3123 | `debug_media` view probing RENDER//var/data |
| `core/management/commands/` | check_media.py:35-39, complete_setup.py:21-22, full_setup.py:15-16, populate_from_images.py:17-18, render_setup.py:27-35, sync_from_ovh.py:16-20, update_flags.py:29-35 | 7 more copies/inline variants of the media-root switch |
| `scripts/` (all 5) | deploy_import.py:14 (settings_production), import_data.py:4, migrate_ovh_to_render.py, setup_render.py, upload_images_to_render.py:7 (onrender.com) | Render migration tooling — delete |
| `templates/admin_sync_ovh.html` | whole file | UI for the FTP sync |

**`get_media_root()` landmine count: 6 verbatim function copies** (models.py:13, middleware.py:18, complete_setup.py:21, full_setup.py:15, populate_from_images.py:17, sync_from_ovh.py:16) **plus 6 inline re-implementations** (settings.py:112-119, update_flags.py:29-35, check_media.py:35-39, render_setup.py:27-35, views.py:3068-3074, start.sh:13-32). All must collapse to `settings.MEDIA_ROOT` read from env.

---

## 3. Settings hygiene

- **SECRET_KEY**: real key `django-insecure-<redacte>...` committed as the fallback in `settings.py:16`, hardcoded outright in `settings_production.py:8` and `simple_app.py:12`. Must rotate and make env-mandatory (no default).
- **ALLOWED_HOSTS = ['*']** — `settings.py:20` and `settings_production.py:11-16`. Replace with `collections.samathey.fr` + VPS hostname from env.
- **CSRF_TRUSTED_ORIGINS** (`settings.py:143-148`): drop onrender wildcard. Note the **domain inconsistency**: site is `collections.samathey.fr` (also hardcoded in `sitemap_xml`, views.py:43) but email defaults use `collection-samathey.com` (settings.py:210-215).
- **Proxy/TLS**: `SECURE_SSL_REDIRECT=True` when not DEBUG (settings.py:151-156) but **no `SECURE_PROXY_SSL_HEADER`** — behind nginx this causes a redirect loop unless `X-Forwarded-Proto` is honored. No HSTS settings.
- **Email** (settings.py:201-224): Hostinger SMTP with hardcoded defaults; `ADMIN_EMAILS` hardcoded (218) and duplicated in `views.py:107`. `EMAIL_HOST_PASSWORD` default `''` — silent failures. Sent synchronously in request path (register/contact, views.py:139-233, 236-314).
- **DB** (settings.py:68-80): `dj_database_url` + `conn_max_age=600`, SQLite fallback — fine; keep DATABASE_URL on OVH (postgres container or managed).
- **No `CACHES` configured, no `SESSION_ENGINE`** → DB-backed sessions, default LocMem cache unused. Nothing in the codebase uses Django's cache framework at all.
- **WhiteNoise** (settings.py:35, 103): `CompressedManifestStaticFilesStorage` — fine, keep; media is explicitly NOT whitenoise (custom middleware, see §1.3).
- **Logging** (settings.py:163-189): `core` logger at **DEBUG** in production → MediaServeMiddleware logs every media lookup. Raw `print()` calls in the hot path: settings.py:125-126, search debug prints per search request (views.py:455-457, 516-529), browse print (1255).
- **Uploads**: `FILE_UPLOAD_MAX_MEMORY_SIZE`/`DATA_UPLOAD_MAX_MEMORY_SIZE` = 100MB (settings.py:192-193) → 100MB buffered in RAM per upload per worker.
- **Unauthenticated debug endpoints in production**: `/debug/browse/`, `/debug/media/`, `/debug/postcard/<id>/` (core/urls.py:85-87) leak MEDIA_ROOT paths, env state, DB counts. `debug_email` and `debug_search` views exist (views.py:3228, 3126) but are unrouted (dead unless re-added).
- **robots.txt is broken**: `views.robots_txt` renders template `'robots.txt'` (views.py:38) but the file on disk is `templates/robot.txt.txt` → `TemplateDoesNotExist` → 500 on `/robots.txt`.
- `core/templatestags/` is misnamed (should be `templatetags`), has no `__init__.py`, and `custom_filters.py` is never `{% load %}`ed — dead package.
- Personal data committed: `db_cp_16_02_2024.csv` / `export-251221_db.csv` contain names, street addresses, private notes (repo root). No `.gitignore`/`.env` present.

---

## 4. Query hotspots and code defects

- **`search_postcards`** (views.py:437-542): pulls the **entire table** into Python (`list(base_queryset.values(...))`, 463), scores in Python per request, then orders with a `Case(*[When(pk=..)...])` of up to N clauses (537-540) — O(N) SQL text. Plus `postcards.count()` re-runs the whole thing for SearchLog (1248). Move to `icontains`/trigram/FTS with an index, or precomputed normalized columns.
- **AnalyticsTrackingMiddleware** (middleware.py:150-374): per tracked page view calls `get_location_from_ip` **3×** (236, 276, 351) — each a DB lookup, and on IP-cache miss up to **2 blocking external HTTP calls with 3s timeouts each** (`core/utils.py:67-113`, ip-api.com then ipapi.co) — the user waits, since middleware runs before the response returns. Also 3+ writes per page view (PageView insert 246, VisitorSession get_or_create/update 284-323, `is_returning` exists-scan over all sessions by IP 327-329, RealTimeVisitor update_or_create 360). `PageView`/`VisitorSession`/`UserActivity` grow unbounded — no retention job.
- **`like_postcard`** (views.py:1545): same blocking geolocation HTTP call in the like AJAX path.
- **`admin_dashboard`** (views.py:1914-2421): ~**250 queries per load** — daily_stats loop = 30 days × 6 counts (2268-2280), hourly = 24 counts (2252-2261), plus ~40 aggregate/count queries scattered through 1944-2247; plus the 500-card disk scan (1968-1971) and media globs (2330-2335). `DailyAnalytics`/`HourlyAnalytics` pre-aggregation models exist (models.py:707, 344) but **nothing populates or reads them**.
- **`profile_view`** (views.py:736-822): ~10 count queries + per-connection loop (784-800) = 3 queries × up to 20 connections ≈ 60 extra queries; `CustomUser.objects.get` inside loop (786).
- **`get_public_postcards`** (views.py:1822-1846): `p.comments.count()` per row (1843) — N+1 despite `prefetch_related`.
- **Broken endpoints**: `admin_detailed_stats_api` uses `Max`/`Min` (views.py:3345-3346) which are **not imported** (only `Sum, Avg, F, Q, Count` at :16) → NameError/500. `admin_export_analytics` uses `csv` at :3654 with no module-level import (only local `import csv` inside `admin_export_data` at :2908) → NameError — but it's **unreachable anyway** because `api/admin/export/` is registered twice (core/urls.py:71 → stub `admin_export_data` returning "No data available", :82 → the real exporter; first wins). Also duplicated: `api/admin/geographic/` (:69 vs :75) and `api/admin/ip/<ip>/` (:70 vs :76).
- **`order_by('?')`** (full-table random sort) in home:1214, gallery:1345, la_poste:1657+1659, get_postcards_for_cover:1142.
- Broad `except Exception → HttpResponse(traceback)` leaks stack traces to anonymous users in home (1227), browse (1297), animated_gallery (1339), gallery (1351), admin_dashboard (2421).
- `admin_users_api` (2707-2724) serializes every user unbounded; `admin_export_analytics` would iterate full tables row-by-row.
- Unrouted dead view: `gallery` (views.py:1342) has no URL.

---

## 5. What the OVH VPS migration must do (inventory for implementers)

**Target shape (docker-compose or systemd, nginx in front):**
1. **nginx** terminates TLS (Let's Encrypt), serves `location /media/ { alias /srv/le-postier/media/; expires 365d; add_header Cache-Control "public, immutable"; }` (native Range support for mp4) and optionally `/static/` from `staticfiles/`; proxies the rest to gunicorn with `X-Forwarded-Proto`.
2. **Django**: delete `MediaServeMiddleware` (core/middleware.py:25-147 + settings.py:42); `MEDIA_ROOT=/srv/le-postier/media` from env; add `SECURE_PROXY_SSL_HEADER`, HSTS, env-driven `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`SECRET_KEY` (no default); delete `settings_production.py` and the `manage.py:9-13` switch; keep whitenoise or move static to nginx.
3. **Gunicorn**: `--workers = 2×CPU+1` (not fixed 2), behind nginx; systemd unit or compose service; healthcheck endpoint.
4. **Postgres**: compose service with volume, or keep DATABASE_URL to managed DB; nightly `pg_dump` + media rsync backup (nothing exists today).
5. **Media transfer**: one-time rsync of the four `postcards/{Vignette,Grande,Dos,Zoom}` trees + `animated_cp` + `signatures`/`covers` to the VPS volume; then run a **filename normalization pass** (lowercase extensions, zero-padded stems) so the 8-extension probing and the case-insensitive middleware fallback become permanently unnecessary; verify with `scan_media`.
6. **Delete** the Render/FTP tooling listed in §2 and consolidate the 8 CSV importers to `import_csv.py`.

**The media-path caching refactor must touch:**
- **Schema** (migration on `Postcard`): either explicit fields (`vignette_file`, `grande_file`, `dos_file`, `zoom_file`, `animation_files` JSON, `has_animation` bool indexed) or a single `media_map` JSONField + `has_animation` bool. `SentPostcard` methods (models.py:570-588) then read from the related Postcard's stored values.
- **Population**: extend `update_flags.py` — its `build_index` (update_flags.py:74-96) already resolves padded/unpadded stems in one directory listing per folder; persist resolved relative paths + animation list via `bulk_update`. Hook it: (a) after `admin_upload_media` (views.py:2921-2957) for the single uploaded file, (b) after `admin_add_postcard` (views.py:3308 currently calls the scanning `update_image_flags`), (c) cron/manual command post-rsync.
- **Model**: rewrite `get_vignette_url/get_grande_url/get_dos_url/get_zoom_url/get_animated_urls/has_animation/get_first_video_url/video_count` (models.py:254-316) to string-concatenate `MEDIA_URL + stored path` — zero I/O.
- **Views reading scans today**: views.py:1148-1150, 1217, 1307, 1490-1494, 1525, 1660, 1773, 1970, 2665-2666, 2815-2819 (plus debug 3014-3018, 3057, 3116-3118).
- **Templates**: browse.html:364-369, 373, 393, 427, 623-629; animated_gallery.html:76-115; la_poste.html:124, 191, 279, 604-620; profile.html:304, 361, 425.
- **Admin**: `core/admin.py:18, 90-93` (`has_images` column → use DB field).
- **Views filtering**: `animated_gallery` becomes `Postcard.objects.filter(has_animation=True)` (views.py:1303-1312); `home` picks 15 animated directly instead of scanning 30 randoms (1212-1221); `la_poste` animated picker likewise (1659-1660); `admin_dashboard` animated_count becomes one `COUNT(*)` (1968-1972).
- **Template calls in Django templates are attribute-style** (`{{ postcard.get_vignette_url }}`) so property/field renames keep templates working if names are preserved.

---

## 6. Landmines (things that will bite the implementer)

1. **Split-brain settings**: `manage.py` uses `settings_production` under RENDER while `wsgi.py` uses `settings` — any historical command output (migrations, flags) may reflect a different MEDIA_ROOT/DB than the running site.
2. **12 copies of the media-root decision** (§2) — miss one and half the commands write to the wrong disk.
3. **Hardcoded superuser creds in repo** (`create_admin.py:10-12`) executed on every build (`build.sh:24`).
4. **Committed real SECRET_KEY** in 3 files; rotating it invalidates all sessions/verification tokens — plan it with the cutover.
5. **No pagination anywhere in browse** — moving media URLs to DB alone won't fix the multi-MB double-serialized HTML (browse.html:358-441 + 616-632); server-side pagination or a JSON catalogue endpoint is part of the perf fix, and is also the design-overhaul surface.
6. **Filename chaos is load-bearing**: 8-extension probing (models.py:239) + unpadded fallback (246-250) + case-insensitive middleware fallback (middleware.py:102-147) all exist because files on the Render disk have mixed case/padding. Normalize filenames during the rsync or the DB cache must store the exact filename found.
7. **`video_count` name collision** (method models.py:315 vs instance attr views.py:1309) — pick one during refactor.
8. **Duplicate/broken admin URLs and missing imports** (§4) — the dashboard mostly works only because the broken endpoints are the duplicated/unreached ones.
9. **Analytics middleware blocks responses on 3rd-party geo APIs** (45 req/min free tier) — under real VPS traffic this rate-limits and adds 3-6s stalls; move to GeoLite2 local DB or queue it.
10. **`/robots.txt` 500s** today (template misnamed `robot.txt.txt`), and sitemap/base URL hardcoded (views.py:43).
11. Unbounded analytics tables (PageView, VisitorSession, UserActivity, SearchLog, PostcardInteraction) with no retention/aggregation job despite `DailyAnalytics`/`HourlyAnalytics` models existing unused.
12. Unauthenticated `/debug/*` endpoints and traceback-leaking exception handlers must not survive the migration.


## Issues (flat list)

- core/models.py:225-252 _find_local_image performs 2-17 stat() syscalls per call (8-extension x 2-name probing) with zero caching; called 9x per card per browse render
- core/models.py:268-297 get_animated_urls costs 13 stat() calls per card with no animation (i=0 loop always probed); has_animation/get_first_video_url/video_count each re-run the full scan; no has_animation DB field exists
- templates/browse.html:364-369,373,393,427,623-629 + core/views.py:1234-1297: browse renders ALL ~1,900 cards with no server-side pagination, 9 image lookups + 6 animation scans per card = ~180,000-440,000 stat() calls and a multi-MB doubly-serialized HTML response per anonymous page view
- core/views.py:1300-1312 animated_gallery iterates every Postcard calling get_animated_urls (~25,000 stats/request); views.py:1309 shadows the video_count model method with an instance attribute
- core/views.py:1657-1660 la_poste scans 200 random cards via has_animation() (~2,600 stats) plus >=210 template vignette lookups; views.py:1968-1971 admin_dashboard scans 500 cards (~6,500 stats)
- core/middleware.py:25-147 MediaServeMiddleware serves all media through gunicorn (2 sync workers), placed last in MIDDLEWARE (settings.py:42) so every image passes session/auth/CSRF middleware; case-insensitive fallback iterdir()s the whole ~2,000-file directory per miss; only 24h Cache-Control, no ETag
- get_media_root()/Render media-root logic duplicated 12 times: models.py:13, middleware.py:18, complete_setup.py:21, full_setup.py:15, populate_from_images.py:17, sync_from_ovh.py:16 (verbatim copies) + settings.py:112-119, update_flags.py:29-35, check_media.py:35-39, render_setup.py:27-35, views.py:3068-3074, start.sh:13-32 (inline variants)
- manage.py:9-13 switches to settings_production under RENDER while wsgi.py:13 always uses settings - management commands and the web process ran with different MEDIA_ROOT/middleware/CSRF config
- le_postier/settings.py:16 + settings_production.py:8 + simple_app.py:12: real SECRET_KEY committed in three places; settings.py:20 ALLOWED_HOSTS=['*']; settings.py:143-148 CSRF trusts *.onrender.com; no SECURE_PROXY_SSL_HEADER or HSTS for an nginx deployment
- core/management/commands/create_admin.py:10-12 hardcodes superuser credentials samathey/<mot-de-passe-redacte> in the repo, printed to stdout, and build.sh:24 runs it on every deploy
- core/middleware.py:236,276,351 + core/utils.py:67-113: analytics middleware calls IP geolocation 3x per page view with up to two blocking 3s external HTTP calls before the response returns, plus 5-8 DB writes/queries per page view; PageView/VisitorSession/UserActivity grow unbounded
- core/views.py:437-542 search_postcards loads the entire postcard table into Python per search and orders via an O(N) Case/When expression; debug prints (455-457,516-529,1255) run per request in production
- core/views.py:1914-2421 admin_dashboard issues ~250 queries per load (30x6 daily counts at 2268-2280, 24 hourly counts at 2252-2261) while DailyAnalytics/HourlyAnalytics pre-aggregation models (models.py:707,344) are never populated or read
- core/views.py:3345-3346 uses Max/Min without importing them (NameError -> admin_detailed_stats_api 500s); views.py:3654 uses csv without module-level import; core/urls.py registers api/admin/export/ (71 vs 82), api/admin/geographic/ (69 vs 75) and api/admin/ip/ (70 vs 76) twice, making admin_export_analytics dead code
- core/urls.py:85-87 exposes unauthenticated /debug/browse/, /debug/media/, /debug/postcard/<id>/ in production; home/browse/animated_gallery/gallery/admin_dashboard return raw tracebacks to anonymous users on exception (views.py:1227,1297,1339,1351,2421)
- views.py:38 renders template 'robots.txt' but the file is templates/robot.txt.txt -> /robots.txt returns 500; sitemap base URL hardcoded (views.py:43); email domain (collection-samathey.com, settings.py:210-215) mismatches site domain (collections.samathey.fr)
- core/admin.py:18,90-93 PostcardAdmin list_display 'has_images' calls check_has_vignette() -> disk scan per row on every admin list page
- settings.py:182-188 sets the core logger to DEBUG in production (MediaServeMiddleware logs every media lookup); settings.py:125-126 print()s at import; FILE_UPLOAD_MAX_MEMORY_SIZE=100MB buffers uploads in RAM (192-193)
- Repo hygiene: db_cp_16_02_2024.csv / export-251221_db.csv with personal data (names, street addresses, card messages) committed at root; no .gitignore/.env; core/templatestags/ misnamed and unloadable; '__init__ - Copie (3).py'/'(4).py' junk in management/commands; 8 overlapping CSV import commands; stray core/import_csv_update.py app-level module; populate_test_data.py is empty; gallery view unrouted
- order_by('?') full-table random sorts on hot paths: views.py:1142,1214,1345,1657,1659; get_public_postcards N+1 comment counts (views.py:1843); profile_view ~60 queries via per-connection loop (views.py:784-800); admin_users_api unbounded serialization (2707-2724)


## Quick wins

- Add has_animation (bool, indexed) + cached media path fields to Postcard and extend update_flags.py's existing build_index (update_flags.py:74-96) to populate them; rewrite models.py:254-316 getters as MEDIA_URL string concatenation - eliminates ~99% of per-request filesystem I/O with no template changes (template calls are attribute-style)
- On the OVH VPS, serve /media/ directly from nginx (alias + expires 365d + Cache-Control immutable) and delete MediaServeMiddleware (core/middleware.py:25-147, settings.py:42) - removes Python from every image/video byte and fixes mp4 range/seek
- Add server-side pagination (Paginator, ~24-48/page) to browse (views.py:1234-1297) and delete the duplicate allPostcardsData inline-JS serialization (browse.html:616-632) - turns a multi-MB page into a normal one
- Rotate SECRET_KEY and make it env-mandatory; delete create_admin.py hardcoded credentials (replace with DJANGO_SUPERUSER_* env vars + createsuperuser --noinput); set ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS from env
- Remove the three duplicated URL registrations in core/urls.py (69-71 vs 75-76, 82), add 'from django.db.models import Max, Min' and module-level 'import csv' to views.py - unbreaks two admin API endpoints for free
- Remove /debug/* routes (core/urls.py:85-87), replace traceback-leaking except blocks with logged 500s, set the core logger to INFO, and strip the per-request print() debugging in search_postcards and settings.py
- Rename templates/robot.txt.txt to robots.txt (fixes the 500 on /robots.txt)
- Collapse get_media_root's 12 copies to plain settings.MEDIA_ROOT from env, then delete start.sh, build.sh, fix_deployment.sh, sync_images.sh, simple_app.py, runtime.txt, settings_production.py, scripts/*, and the Render/FTP management commands in one sweep (inventory in report section 2)
- Replace the blocking ip-api.com/ipapi.co calls (core/utils.py:67-113) with a local GeoLite2 lookup or defer geolocation to a background task; call get_location_from_ip once per request instead of 3x (middleware.py:236,276,351)
- Feed admin_dashboard from the already-modeled DailyAnalytics/HourlyAnalytics tables via a nightly aggregation command instead of ~250 live queries; replace the 500-card disk scan (views.py:1968-1971) with COUNT(has_animation=True)