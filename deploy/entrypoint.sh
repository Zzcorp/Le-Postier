#!/bin/sh
# Entrypoint du conteneur web : migrations + collectstatic, puis gunicorn.
# (Rien de tout cela ne se fait au build de l'image : la base et le .env
# n'existent qu'à l'exécution.)
set -e

echo "[entrypoint] Application des migrations..."
python manage.py migrate --noinput

echo "[entrypoint] Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Nombre de workers gunicorn : WEB_CONCURRENCY si défini dans le .env,
# sinon la règle classique 2 x CPU + 1.
if [ -z "${WEB_CONCURRENCY:-}" ]; then
    CPUS="$(nproc 2>/dev/null || echo 1)"
    WEB_CONCURRENCY=$((CPUS * 2 + 1))
fi

echo "[entrypoint] Démarrage de gunicorn (${WEB_CONCURRENCY} workers)..."
exec gunicorn le_postier.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${WEB_CONCURRENCY}" \
    --timeout 60 \
    --graceful-timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile - \
    --error-logfile -
