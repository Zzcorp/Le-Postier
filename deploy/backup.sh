#!/bin/sh
# Le Postier — sauvegarde nocturne (lancée par cron sur l'hôte, voir
# DEPLOY_OVH.md §9) : dump Postgres compressé + miroir rsync des médias.
#
# Restauration : voir DEPLOY_OVH.md §11.
set -eu

APP_DIR="/srv/lepostier/app"
MEDIA_DIR="/srv/lepostier/media"
BACKUP_DIR="/srv/lepostier/backups"
KEEP_DAYS=14

STAMP="$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR/db" "$BACKUP_DIR/media"

# 1. Dump de la base — via le conteneur db (les variables POSTGRES_* sont
#    déjà définies dans ce conteneur). --clean --if-exists rend le dump
#    directement restaurable sur une base existante.
cd "$APP_DIR"
docker compose exec -T db sh -c 'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    | gzip > "$BACKUP_DIR/db/lepostier-$STAMP.sql.gz"

# 2. Miroir des médias (incrémental : seuls les fichiers nouveaux/modifiés
#    sont copiés).
rsync -a --delete "$MEDIA_DIR/" "$BACKUP_DIR/media/"

# 3. Rotation : on garde KEEP_DAYS jours de dumps.
find "$BACKUP_DIR/db" -name '*.sql.gz' -mtime +"$KEEP_DAYS" -delete

echo "[backup] OK $STAMP — $(du -sh "$BACKUP_DIR" | cut -f1) au total"
