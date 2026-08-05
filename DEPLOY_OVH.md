# Déployer Le Postier sur un VPS OVHcloud

Guide complet, dans l'ordre, pour installer le site sur un VPS OVH (Ubuntu 24.04)
avec Docker : nginx (TLS Let's Encrypt) → gunicorn/Django → Postgres 16, médias
servis directement par nginx. Chaque commande est à copier telle quelle, sauf
mention contraire (les valeurs à remplacer sont `EN_MAJUSCULES_ENTRE_CHEVRONS`).

Domaine utilisé partout : **collections.samathey.fr**. Si le domaine change un
jour, il apparaît dans `.env` et dans `deploy/nginx.conf`.

Arborescence cible sur le serveur :

```
/srv/lepostier/
├── app/        ← ce dépôt (docker compose s'exécute ici)
├── media/      ← les images/vidéos des cartes (servies par nginx)
└── backups/    ← dumps nocturnes de la base + miroir des médias
```

---

## 1. Vue d'ensemble

| Conteneur | Rôle |
|---|---|
| `nginx` | Ports 80/443, TLS, sert `/media/` directement, proxifie le reste |
| `web` | Django + gunicorn (migrations et collectstatic au démarrage) |
| `db` | Postgres 16 (volume Docker `pgdata`) |
| `certbot` | Renouvelle les certificats Let's Encrypt en boucle (12 h) |

Étapes : VPS + DNS → sécurisation → Docker → code + `.env` → premier
certificat TLS → premier démarrage → récupération des données Render →
médias → cron. Comptez une à deux heures.

## 2. Commander le VPS et pointer le DNS

1. Sur [ovhcloud.com](https://www.ovhcloud.com/fr/vps/), commander un VPS
   (2 vCPU / 4 Go RAM / 80 Go suffisent largement) avec **Ubuntu 24.04**.
   Ajouter votre **clé SSH publique** dans l'espace client au moment de la
   commande si l'option est proposée.
2. Notez l'adresse IP publique du VPS (email de livraison OVH).
3. Chez le registrar qui gère `samathey.fr`, créez un enregistrement DNS :

   ```
   Type A    Nom : collections    Cible : <IP_DU_VPS>    TTL : 3600
   ```

4. Vérifiez la propagation (depuis votre machine) :

   ```bash
   nslookup collections.samathey.fr
   ```

   Tant que l'IP renvoyée n'est pas celle du VPS, attendez — le certificat
   TLS (étape 6) ne peut pas être émis avant.

## 3. Sécuriser le serveur

Connectez-vous (utilisateur `ubuntu` sur les VPS OVH Ubuntu) :

```bash
ssh ubuntu@<IP_DU_VPS>
```

Mises à jour puis pare-feu (SSH + web uniquement) :

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable        # répondre y
sudo ufw status
```

Si vous n'avez pas fourni de clé SSH à la commande : copiez-la maintenant
(`ssh-copy-id ubuntu@<IP_DU_VPS>` depuis votre machine), vérifiez que la
connexion par clé fonctionne, puis désactivez le mot de passe :

```bash
sudo sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

## 4. Installer Docker

Dépôt officiel Docker (la version Ubuntu est trop vieille) :

```bash
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```

**Déconnectez-vous puis reconnectez-vous** (pour que le groupe `docker` soit
pris en compte), puis vérifiez :

```bash
docker compose version
```

## 5. Installer le site (code, dossiers, .env)

```bash
sudo mkdir -p /srv/lepostier/app /srv/lepostier/media /srv/lepostier/backups
sudo chown -R $USER:$USER /srv/lepostier
git clone <URL_DU_DEPOT_GIT> /srv/lepostier/app
cd /srv/lepostier/app
# Le dépôt est développé sous Windows : normaliser les scripts shell
sed -i 's/\r$//' deploy/*.sh && chmod +x deploy/*.sh
```

Créez le `.env` de production à partir du modèle :

```bash
cp .env.example .env
```

Générez les deux secrets :

```bash
# SECRET_KEY Django — ATTENTION : la changer plus tard invalide toutes les
# sessions et les codes de vérification en attente.
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
# Mot de passe Postgres
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

Éditez le fichier (`nano .env`) et remplissez :

```ini
SECRET_KEY=<PREMIERE_VALEUR_GENEREE>
DEBUG=False
ALLOWED_HOSTS=collections.samathey.fr,127.0.0.1
SITE_URL=https://collections.samathey.fr
CSRF_TRUSTED_ORIGINS=https://collections.samathey.fr

DATABASE_URL=postgres://lepostier:<MOT_DE_PASSE_POSTGRES>@db:5432/lepostier
POSTGRES_DB=lepostier
POSTGRES_USER=lepostier
POSTGRES_PASSWORD=<MOT_DE_PASSE_POSTGRES>

# MEDIA_ROOT reste vide : docker-compose impose /data/media dans le conteneur.
MEDIA_ROOT=

EMAIL_HOST_PASSWORD=<MOT_DE_PASSE_SMTP_HOSTINGER>
```

Le reste des valeurs par défaut de `.env.example` convient.

## 6. Premier certificat TLS (bootstrap)

nginx refuse de démarrer tant que le certificat n'existe pas ; on obtient donc
le premier certificat **avant** de lancer la pile, avec le serveur intégré de
certbot sur le port 80 (libre à ce stade). Le DNS doit déjà pointer sur le VPS
(étape 2.4).

```bash
cd /srv/lepostier/app
docker compose run --rm -p 80:80 --entrypoint certbot certbot \
  certonly --standalone -d collections.samathey.fr \
  --email sam@samathey.com --agree-tos --no-eff-email
```

Succès = « Successfully received certificate ». Les renouvellements suivants
sont automatiques (conteneur `certbot`, via le webroot servi par nginx).

## 7. Premier démarrage et compte administrateur

```bash
cd /srv/lepostier/app
docker compose up -d --build
docker compose ps          # les 4 services doivent être Up ; web devient "healthy"
docker compose logs -f web # Ctrl+C pour quitter ; on doit voir migrations + collectstatic + gunicorn
```

Ouvrez https://collections.samathey.fr — le site répond (base encore vide).

Créez le compte super-administrateur (remplacez les trois valeurs) :

```bash
docker compose exec \
  -e DJANGO_SUPERUSER_USERNAME=<IDENTIFIANT> \
  -e DJANGO_SUPERUSER_EMAIL=<EMAIL> \
  -e DJANGO_SUPERUSER_PASSWORD='<MOT_DE_PASSE_FORT>' \
  web python manage.py createsuperuser --noinput
```

(Ou en interactif : `docker compose exec -it web python manage.py createsuperuser`.)

## 8. Récupérer les données et les médias de Render

### 8.1 La base de données

Dans le tableau de bord Render, ouvrez la base Postgres et copiez
l'**External Database URL** (elle commence par `postgres://` et contient le
mot de passe). Puis, sur le VPS :

```bash
cd /srv/lepostier/app
# 1. Arrêter le site le temps de la restauration
docker compose stop web

# 2. Exporter depuis Render (le dump transite par le conteneur db)
docker compose exec -T db pg_dump --no-owner --no-privileges --clean --if-exists \
  "<EXTERNAL_DATABASE_URL_RENDER>" > /srv/lepostier/backups/render-export.sql
# En cas d'erreur SSL, ajoutez ?sslmode=require à la fin de l'URL.

# 3. Restaurer dans la base locale
docker compose exec -T db psql -U lepostier -d lepostier \
  < /srv/lepostier/backups/render-export.sql

# 4. Redémarrer le site — les nouvelles migrations (cache des médias, etc.)
#    s'appliquent automatiquement au démarrage
docker compose start web
docker compose logs -f web
```

### 8.2 Les médias

Depuis la machine qui détient une copie complète des médias (copie locale, ou
le disque Render via son shell SSH), envoyez les arborescences vers le VPS.
Structure attendue à l'arrivée :

```
/srv/lepostier/media/
├── postcards/
│   ├── Vignette/   ├── Grande/   ├── Dos/   └── Zoom/
├── animated_cp/
├── signatures/
└── covers/
```

Depuis Linux, macOS ou Windows + WSL :

```bash
rsync -avz --progress \
  media/postcards media/animated_cp media/signatures media/covers \
  ubuntu@<IP_DU_VPS>:/srv/lepostier/media/
```

(Sous Windows sans WSL, WinSCP fait la même chose en glisser-déposer, vers
`/srv/lepostier/media/`.)

**Option FTP — récupérer les médias directement depuis votre serveur FTP OVH.**
Si les images et vidéos des cartes vivent sur votre hébergement FTP OVH
(arborescence `/collection_cp/cartes/{Vignette,Grande,Dos,Zoom}` +
`/collection_cp/cartes/animated_cp`), la commande historique `sync_from_ovh`
télécharge tout directement dans le volume médias du VPS — aucun rsync
nécessaire :

```bash
cd /srv/lepostier/app
# Test à blanc (liste ce qui serait téléchargé) :
docker compose exec \
  -e OVH_FTP_HOST=ftp.votre-domaine.fr \
  -e OVH_FTP_USER=votre_login \
  -e OVH_FTP_PASS='votre_mot_de_passe' \
  web python manage.py sync_from_ovh --dry-run

# Téléchargement complet (reprend là où il s'est arrêté : les fichiers
# déjà présents sont ignorés — relançable sans risque) :
docker compose exec \
  -e OVH_FTP_HOST=ftp.votre-domaine.fr \
  -e OVH_FTP_USER=votre_login \
  -e OVH_FTP_PASS='votre_mot_de_passe' \
  web python manage.py sync_from_ovh

# Puis, obligatoirement, reconstruire l'index des médias :
docker compose exec web python manage.py rebuild_media_index
```

Si votre arborescence FTP diffère, ajustez `--ftp-path` (défaut
`/collection_cp/cartes`) et `--animated-path`. Les commandes sœurs
`import_from_ftp` et `sync_images_from_ftp` existent aussi si vous en aviez
l'habitude ; toutes écrivent au même endroit et se terminent par le même
`rebuild_media_index`.

Puis, sur le VPS, donnez la main au conteneur (l'utilisateur applicatif a
l'UID 1000) et construisez l'index des médias :

```bash
sudo chown -R 1000:1000 /srv/lepostier/media
cd /srv/lepostier/app
docker compose exec web python manage.py rebuild_media_index
docker compose exec web python manage.py rebuild_media_index --check   # signale les fichiers orphelins
```

À partir d'ici le site est complet : vérifiez la page Parcourir, une carte en
grand (recto/verso), une carte animée, et l'admin.

**Note — noms de fichiers (facultatif).** L'index stocke les noms *exactement
tels qu'ils existent* sur le disque (majuscules, extensions, numéros non
complétés). Aucune normalisation n'est nécessaire. Si un jour vous renommez ou
normalisez des fichiers, relancez simplement `rebuild_media_index`.

## 9. Tâches planifiées (cron)

```bash
crontab -e
```

Ajoutez ces lignes :

```cron
# Le Postier — sauvegarde nocturne (base + médias) à 03h15
15 3 * * * /srv/lepostier/app/deploy/backup.sh >> /srv/lepostier/backups/backup.log 2>&1

# Le Postier — agrégation des statistiques + purge des données brutes (>90 j) à 03h45
45 3 * * * cd /srv/lepostier/app && /usr/bin/docker compose exec -T web python manage.py aggregate_analytics >> /srv/lepostier/backups/analytics.log 2>&1

# Le Postier — certbot : le conteneur renouvelle les certificats en continu ;
# on recharge nginx chaque lundi pour prendre en compte un éventuel nouveau certificat
30 4 * * 1 cd /srv/lepostier/app && /usr/bin/docker compose exec -T nginx nginx -s reload
```

**Recommandé :** les sauvegardes restent sur le disque du VPS. Activez en plus
une copie externe — l'option « Automated Backup » du VPS dans l'espace client
OVH, ou un `rsync` de `/srv/lepostier/backups/` vers une autre machine.

## 10. Mettre à jour le site

Après chaque modification poussée sur le dépôt :

```bash
cd /srv/lepostier/app
git pull
docker compose build web
docker compose up -d web
docker compose logs -f web   # vérifier migrations + collectstatic + gunicorn
```

Les migrations et `collectstatic` s'exécutent automatiquement au démarrage du
conteneur. `nginx`, `db` et `certbot` n'ont pas besoin d'être redémarrés.

## 11. Restaurer une sauvegarde

Base de données (les dumps sont auto-restaurables : ils recréent les tables) :

```bash
cd /srv/lepostier/app
docker compose stop web
gunzip -c /srv/lepostier/backups/db/lepostier-<DATE>.sql.gz \
  | docker compose exec -T db psql -U lepostier -d lepostier
docker compose start web
```

Médias :

```bash
rsync -a /srv/lepostier/backups/media/ /srv/lepostier/media/
sudo chown -R 1000:1000 /srv/lepostier/media
cd /srv/lepostier/app && docker compose exec web python manage.py rebuild_media_index
```

## 12. Notes et dépannage

- **HSTS** : le site démarre avec `SECURE_HSTS_SECONDS=3600` (1 h). Après
  quelques semaines de HTTPS sans incident, passez à `31536000` (1 an) dans
  `.env` puis `docker compose up -d web`.
- **Rotation de la SECRET_KEY** : possible, mais elle déconnecte tous les
  utilisateurs et invalide les codes de vérification en cours.
- **Un service ne démarre pas** : `docker compose logs <service>` ;
  état général : `docker compose ps`.
- **502 Bad Gateway** : `web` est probablement en train de démarrer (ou en
  échec) — `docker compose logs -f web`.
- **Erreur CSRF sur les formulaires** : vérifiez `CSRF_TRUSTED_ORIGINS` dans
  `.env` (schéma `https://` inclus).
- **Espace disque** : `df -h` ; les images Docker orphelines se nettoient avec
  `docker system prune -f`.
- **Emails non reçus** : vérifiez `EMAIL_HOST_PASSWORD` dans `.env`, puis
  `docker compose logs web | grep -i mail`.
