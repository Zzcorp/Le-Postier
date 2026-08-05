# Le Postier — Implementation Plan (redesign + OVH VPS migration)

This is the coordination contract for all implementation work. It is authoritative alongside
`DESIGN_SPEC.md` (visual/UX system). Audit evidence lives in `audit-*.md` in this folder.

Target stack: **Django 5.2 LTS** (venv at `.venv/`, already installed), Postgres 16 in production,
SQLite in dev, docker-compose + nginx + gunicorn on an OVHCloud VPS. No build step, no CDN.

Pre-provisioned shared assets (already on disk — do not re-download):
- `static/fonts/*.woff2` + `static/fonts/fonts.css` (@font-face blocks, latin subsets:
  Cormorant Garamond 500/600/500i, EB Garamond 400/500/600/400i, Inter 400/500/600, Caveat 400/600)
- `static/js/vendor/chart.umd.js` (Chart.js 4.4.9, for admin only)
- `static/images/ui/paper-grain.png` (cabinet texture, use at ~3% opacity)

---

## 1. File ownership (hard rule — never edit a file owned by another workstream)

| Workstream | Owns |
|---|---|
| **foundation** | `static/css/tokens.css` (new), `static/css/base.css` (rewrite), `static/css/components.css` (new), `static/js/main.js` (rewrite), `templates/base.html`, `templates/partials/navbar.html`, `templates/partials/postcard_modal.html` (rebuild as shared vitrine dialog), NEW `templates/partials/postcard_frame.html`, `templates/partials/pagination.html`, `templates/partials/consent.html`, `static/images/ui/postmark.svg` (new, drawn by hand), delete `templates/admin_sync_ovh.html` |
| **backend** | `core/models.py`, `core/views.py`, `core/urls.py`, `le_postier/urls.py`, `core/middleware.py`, `core/utils.py`, `core/admin.py`, `core/forms.py`, `core/migrations/0008_*` (new), `core/management/commands/**` (consolidation), `templates/robots.txt` (rename from `robot.txt.txt`) |
| **deploy** | `le_postier/settings.py`, `manage.py`, `requirements.txt`, `Dockerfile`, NEW `docker-compose.yml`, NEW `deploy/` (nginx.conf, entrypoint.sh, backup.sh), NEW `.env.example`, `.gitignore`, `.dockerignore`, NEW `DEPLOY_OVH.md`, `README.md`, deletion/archival of Render-era files (`start.sh`, `build.sh`, `fix_deployment.sh`, `sync_images.sh`, `simple_app.py`, `runtime.txt`, `le_postier/settings_production.py`, `scripts/`), move the two root CSVs into `data/` (gitignored) |
| **page: browse** | `templates/browse.html`, NEW `static/css/pages/browse.css`, `static/js/browse.js` (rewrite), delete `static/css/browse.css` old + `static/css/gallery.css`, delete `templates/gallery.html` (unrouted dead view; backend removes the view) |
| **page: home-group** | `templates/home.html`, `templates/intro.html`, `templates/presentation.html`, NEW `static/css/pages/home.css`, `static/css/pages/intro.css`, `static/css/pages/presentation.css`, delete old `static/css/home.css`, `static/css/presentation.css` |
| **page: media-group** | `templates/animated_gallery.html`, `templates/decouvrir.html`, NEW `static/css/pages/animated.css`, `static/css/pages/decouvrir.css`, delete `static/js/gallery.js` (0 bytes) |
| **page: social** | `templates/la_poste.html`, `templates/profile.html`, NEW `static/css/pages/la-poste.css`, `static/css/pages/profile.css`, NEW `static/js/la-poste.js`, `static/js/profile.js` |
| **page: auth-contact** | `templates/login.html`, `register.html`, `verify_email.html`, `set_password.html`, `registration_complete.html`, `contact.html`, `emails/verification_code.html`, NEW `static/css/pages/auth.css`, `static/css/pages/contact.css`, delete old `static/css/contact.css` |
| **page: admin** | `templates/admin_dashboard.html`, `static/css/admin_dashboard.css` (rewrite) |

CSS load order (foundation sets it in base.html): `fonts.css` → `tokens.css` → `base.css` →
`components.css` → `{% block extra_css %}` (per-page `pages/*.css`). JS: `main.js` deferred +
`{% block extra_js %}` deferred. **All inline `<style>`/`<script>` blocks move into these files.**

## 2. Template contracts (foundation provides, pages consume)

- `partials/postcard_frame.html` — the passe-partout + cartel tile (DESIGN_SPEC §5.3).
  `{% include 'partials/postcard_frame.html' with postcard=card show_like=True %}`.
  Renders: `<a class="pc-frame" href="…" data-id="{{ card.id }}">` mat → `<img loading="lazy">`
  from `card.get_vignette_url` → cartel (`N°`, title, rarity badge) → like button (if authenticated
  and show_like). Page JS opens the vitrine dialog by intercepting click on `[data-id]`.
- `partials/postcard_modal.html` — ONE shared `<dialog id="vitrine">` per DESIGN_SPEC §5.4,
  included once in `base.html`. `main.js` exposes `window.Vitrine = { open(id, ids), close() }`;
  it fetches `/api/postcard/<id>/`, renders recto/verso flip, zoom layer, like, « Envoyer via
  La Poste » link. Pages pass the ordered id list of the current grid for ←/→ traversal.
- `partials/pagination.html` — `{% include 'partials/pagination.html' with page_obj=page_obj %}`,
  preserves query params (uses `{{ request.GET.urlencode }}` minus `page`).
- `main.js` also exposes: `Toast.show(message, kind)` (aria-live container in base.html),
  `getCookie('csrftoken')`, `postJSON(url, data)`, consent manager (GA loads only after accept;
  `Consent.open()` re-opens preferences), navbar behavior, page-entrance stagger, and the
  coup-de-tampon like animation as a delegated handler on `.pc-like` buttons (used by every page).
- Every page template MUST define: `{% block title %}`, `{% block meta %}` (description + OG),
  `{% block content %}`. The old navbar `page_title` block is dead — foundation removes it.

## 3. Backend contracts (backend provides, pages rely on)

### 3.1 Postcard media cache (migration 0008)
New fields on `Postcard`: `vignette_file`, `grande_file`, `dos_file`, `zoom_file`
(`CharField(max_length=255, blank=True, default='')`, relative to MEDIA_ROOT, exact filename as
found on disk), `animation_files` (`JSONField(default=list)`), `has_animation`
(`BooleanField(default=False, db_index=True)`), `media_synced_at` (`DateTimeField(null=True)`),
`search_blob` (`TextField(blank=True, default='')`, accent-stripped lowercase of
number+title+keywords, maintained on save and by import). `has_images` gets `db_index=True`.
- `get_vignette_url/get_grande_url/get_dos_url/get_zoom_url/get_animated_urls/has_animation()/
  get_first_video_url/video_count` become **zero-I/O** reads of these fields (same public names —
  templates keep working). Fallback chain stays (grande→vignette, zoom→grande) via the fields.
- `refresh_media_cache()` instance method rescans disk for ONE card (used after admin upload).
- Management command **`rebuild_media_index`** (extends the `update_flags.py` build_index pattern:
  one directory listing per folder, padded+unpadded stems, all extensions) → `bulk_update` all
  cards + `media_synced_at`. `--check` mode reports orphans. Old scanning commands
  (`update_postcard_flags`, `scan_media` auto-create parts) fold into it or are deleted.
- `SentPostcard.get_image_url/get_vignette_url/get_video_url` read the related card's cached fields.

### 3.2 View contexts (canonical; templates are built against THIS)
- `home`: `carte_du_jour` (Postcard, deterministic: ordered id list of `has_images=True`, index
  `date.toordinal() % count`), `pieces_choisies` (3 cards, seeded by ISO week, excluding carte du
  jour), `stats = {'total': n_cards, 'animated': n_animated}`. No `order_by('?')`, no disk scans.
- `browse`: GET params `q` (also accepts legacy `search`), `rarete` in
  `{'commune','rare','tres_rare'}`, `tri` in `{'numero' (default),'populaires','recentes'}`,
  `page`. Context: `page_obj` (48/page), `postcards` (= page_obj.object_list), `query`, `rarete`,
  `tri`, `total_count`. Search uses `search_blob` icontains prefilter + existing Python relevance
  scoring on the reduced set. **No full-catalogue serialization to the template.**
- `animated_gallery`: `page_obj` (24/page) over `filter(has_animation=True)`, same param names.
- `decouvrir`, `presentation`, `contact`: unchanged contexts.
- `la_poste`: unchanged context names, minus disk scans; compose picker data now comes from the
  API below (no 200-card random context dump).
- `profile_view` + `profile_connections/favorites/activity/settings`: all render `profile.html`
  with `active_tab` in `{'activite','connexions','favoris','reglages'}` (fixes the 500 routes);
  aggregate counts computed with `annotate`, no per-connection loops.
- Auth views: unchanged names/redirects; `?next=` validated with
  `url_has_allowed_host_and_scheme`.

### 3.3 JSON APIs (shapes pages code against)
- `GET /api/postcard/<id>/` → `{id, number, padded_number, title, description, keywords:[],
  rarity, rarity_label, views_count, likes_count, liked, vignette_url, grande_url, dos_url,
  zoom_url, animation_urls:[], has_animation, can_zoom, locked}`. **Rarity gating enforced
  server-side**: viewers without rights on rare/très-rare get `locked:true`, vignette only,
  empty grande/dos/zoom/animations. Increments views_count (F expression).
- `POST /api/postcard/<id>/like/` → `{success, liked, likes_count}` (existing shape kept; geo
  lookup made non-blocking).
- `GET /api/postcards/picker/?q=&page=` (new, auth required) → `{results:[{id, number, title,
  vignette_url, has_animation}], page, num_pages}` 24/page — used by La Poste compose (replaces
  the random context dump; `get_postcards_for_cover` delegates to it).
- La Poste endpoints keep current URLs/shapes (`send`, `postcards`, `public`, `read`, `comment`,
  `message`, `check-signature`, `users/search`) — send returns the created card's JSON so the list
  updates in place (no reload).
- Admin APIs: fix missing `Max/Min/csv` imports, remove duplicate URL registrations
  (geographic/ip/export), `admin_export_analytics` becomes the routed exporter, dashboard's
  animated count becomes `COUNT(has_animation=True)`, 5-minute LocMem cache on the heavy stats
  endpoints.

### 3.4 Hygiene (backend)
- Delete `/debug/*` routes + views; replace traceback-leaking `except` blocks with logged 500s.
- `AnalyticsTrackingMiddleware`: ONE `get_location_from_ip` per request; cache-first; on cache
  miss record empty location and fetch in a daemon thread (never block a response on ip-api).
- Remove per-request `print()` (search, browse). Rename `templates/robot.txt.txt` →
  `templates/robots.txt`. Sitemap/robots base URL from `settings.SITE_URL`.
- Delete: FTP/Render commands (`sync_from_ovh`, `migrate_from_ovh`, `import_from_ftp`,
  `sync_images_from_ftp`, `quick_sync`, `render_setup`, `complete_setup`, `full_setup`,
  `upload_media`), duplicate importers (keep `import_csv.py` only), `create_admin.py`
  (hardcoded credentials!), junk `__init__ - Copie*.py`, stray `core/import_csv_update.py`,
  empty `populate_test_data.py`, unrouted `gallery` view, dead `core/templatestags/`.
- `django.utils.timezone.timedelta` → `datetime.timedelta`. Django 5.2 compat throughout.
- New command `aggregate_analytics` (nightly): fills `DailyAnalytics`/`HourlyAnalytics`, prunes
  raw `PageView`/`UserActivity`/`SearchLog`/`PostcardInteraction`/`RealTimeVisitor` rows older
  than 90 days.

## 4. Deployment contract (deploy workstream)

- **settings.py** (single settings file, env-driven via decouple): SECRET_KEY **required** (no
  default), `DEBUG` default False, `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`SITE_URL` from env,
  `MEDIA_ROOT` from env (default `BASE_DIR/media`), **`STORAGES` dict (Django 5.2 — the old
  `STATICFILES_STORAGE` was removed in 5.1)** with whitenoise for static, `SECURE_PROXY_SSL_HEADER
  = ('HTTP_X_FORWARDED_PROTO','https')`, HSTS (initially 3600, doc says raise later), logging at
  INFO, `CACHES` LocMem, `EMAIL_TIMEOUT`, admin emails from env. Remove: Render probing, prints,
  `MediaServeMiddleware` from MIDDLEWARE (backend deletes the class; DEBUG media served via
  `static()` helper in `le_postier/urls.py` — backend owns that file). `manage.py` loses the
  settings_production switch.
- **requirements.txt**: `Django>=5.2,<5.3`, `gunicorn`, `whitenoise`, `psycopg[binary]`,
  `dj-database-url`, `python-decouple`, `Pillow`, `requests`, `user-agents`.
- **docker-compose.yml**: `web` (build ., entrypoint runs `migrate` + `collectstatic` then
  gunicorn, `WEB_CONCURRENCY` env, healthcheck, `restart: unless-stopped`), `db` (postgres:16-
  alpine, volume `pgdata`, healthcheck), `nginx` (80/443, mounts `deploy/nginx.conf`, certbot
  webroot + letsencrypt volumes, media bind `/srv/lepostier/media:/media:ro`), `certbot`
  (renew loop). Web mounts the same media path read-write at `/data/media`; `MEDIA_ROOT=/data/media`.
- **nginx.conf**: HTTP→HTTPS redirect + ACME webroot; TLS server: `client_max_body_size 200m`,
  gzip (html/css/js/svg/json), `location /media/ { alias /media/; expires 365d; add_header
  Cache-Control "public, immutable"; }` (mp4 Range works natively), proxy_pass web:8000 with
  X-Forwarded-Proto/Host headers.
- **DEPLOY_OVH.md**: OVH VPS provisioning (Ubuntu 24.04), ssh key + ufw basics, Docker install,
  DNS A record for the domain, `.env` creation (with SECRET_KEY generation command + note that
  rotating invalidates sessions), first `docker compose up`, TLS bootstrap, superuser via
  `DJANGO_SUPERUSER_*` + `createsuperuser --noinput`, **data migration from Render** (`pg_dump`
  from Render DATABASE_URL → restore into the compose db), **media transfer** (rsync the
  `postcards/{Vignette,Grande,Dos,Zoom}`, `animated_cp`, `signatures`, `covers` trees to
  `/srv/lepostier/media`, then `manage.py rebuild_media_index`), nightly backups
  (`deploy/backup.sh`: pg_dump + media rsync, cron line), update procedure, and a
  filename-normalization note (optional; the index stores exact names).

## 5. Order of execution

Phase A (parallel): foundation, backend, deploy — disjoint files by §1.
Phase B (parallel, after A): the six page workstreams — they read the REAL files produced in
Phase A (tokens/components/partials/main.js, new views.py) plus DESIGN_SPEC.md + their audit.
Phase C: verification (fresh sqlite migrate, CSV import, placeholder media, `rebuild_media_index`,
runserver smoke of every route, `manage.py check --deploy`, then adversarial review + fixes).

## 6. Non-negotiables for every workstream

- French UI copy is preserved (restyle, don't rewrite; small additions like consent/footer legal
  links are written in French).
- No CDN references anywhere (GA only after consent). No emoji as UI ornament.
- All user-generated strings rendered via `textContent` in JS (XSS).
- `prefers-reduced-motion` respected; content never hidden behind JS-only reveals.
- WCAG AA per DESIGN_SPEC tokens; 44px touch targets; `:focus-visible` everywhere.
- Old class names may die, but URLs, view names, form fields, and API shapes only change where
  §3 says so.
