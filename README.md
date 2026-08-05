# Le Postier — Collection Samathey

Site de la collection de cartes postales anciennes de la famille Samathey
(collections.samathey.fr) : catalogue consultable (~1 900 cartes, recto/verso,
zoom, cartes animées), « La Poste » (envoi de cartes entre membres), comptes
avec vérification par email, et tableau de bord d'administration.

Pile : Django 5.2 · templates + CSS/JS écrits à la main (aucun build, aucun
CDN) · SQLite en développement, Postgres 16 en production (Docker + nginx +
gunicorn sur VPS OVH).

## Développement local (Windows)

```powershell
# 1. Environnement virtuel + dépendances
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# 2. Configuration — le dépôt contient déjà un .env de développement ;
#    sinon, copier .env.example vers .env (DEBUG=True, ALLOWED_HOSTS=localhost,127.0.0.1,
#    SECRET_KEY générée via : python -c "import secrets; print(secrets.token_urlsafe(50))")

# 3. Base de données (SQLite) + données
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py import_csv data\export-251221_db.csv

# 4. Médias : placer les images dans media\postcards\{Vignette,Grande,Dos,Zoom},
#    les vidéos dans media\animated_cp, puis construire l'index
.venv\Scripts\python manage.py rebuild_media_index

# 5. Lancer
.venv\Scripts\python manage.py runserver
```

Le site répond sur http://127.0.0.1:8000. Les emails s'affichent dans la
console (voir `.env`).

## Production

Le déploiement complet (VPS OVH, Docker, TLS, migration des données,
sauvegardes) est décrit pas à pas dans **[DEPLOY_OVH.md](DEPLOY_OVH.md)**.

## Documentation

- `docs/redesign/DESIGN_SPEC.md` — le système de design « Cachet »
  (couleurs, typographie, composants, mouvement).
- `docs/redesign/MIGRATION_PLAN.md` — le plan d'implémentation et les
  contrats entre les différentes parties du code.
- `docs/redesign/audit-*.md` — les audits de l'existant.

Les exports CSV de la collection vivent dans `data/` (non versionné : ils
contiennent des données personnelles).
