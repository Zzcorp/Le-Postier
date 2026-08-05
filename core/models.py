# core/models.py
import datetime
import secrets
import string
import unicodedata
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

# Extensions found on disk (mixed case is load-bearing until filenames are normalized)
MEDIA_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF']
MEDIA_VIDEO_EXTENSIONS = ['.mp4', '.webm', '.MP4', '.WEBM']


def generate_verification_code():
    """Generate a 6-digit verification code (CSPRNG)"""
    return ''.join(secrets.choice(string.digits) for _ in range(6))


def normalize_search_text(text):
    """Accent-stripped, lowercased text used for the search_blob column."""
    if not text:
        return ''
    normalized = unicodedata.normalize('NFD', str(text))
    stripped = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    return stripped.lower().strip()


class CustomUser(AbstractUser):
    USER_CATEGORIES = [
        ('subscribed_unverified', 'Inscrit - Non vérifié'),
        ('subscribed_verified', 'Inscrit - Vérifié'),
        ('postman', 'Facteur'),
        ('viewer', 'Visiteur privilégié'),
    ]
    category = models.CharField(
        max_length=30,
        choices=USER_CATEGORIES,
        default='subscribed_unverified',
        verbose_name="Catégorie"
    )
    email_verified = models.BooleanField(default=False, verbose_name="Email vérifié")
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True, verbose_name="Code de vérification")
    verification_code_created_at = models.DateTimeField(null=True, blank=True)
    password_set = models.BooleanField(default=True, verbose_name="Mot de passe défini")
    date_joined = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_visit_date = models.DateField(null=True, blank=True)
    last_intro_seen = models.DateField(null=True, blank=True)
    signature_image = models.ImageField(
        upload_to='signatures/',
        blank=True,
        null=True,
        verbose_name="Signature"
    )
    cover_image = models.ImageField(
        upload_to='covers/',
        blank=True,
        null=True,
        verbose_name="Image de couverture"
    )
    bio = models.TextField(blank=True, max_length=500, verbose_name="Biographie")
    country = models.CharField(max_length=100, blank=True, verbose_name="Pays")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    registration_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP d'inscription")

    # Profile customization
    profile_cover = models.ImageField(upload_to='covers/', blank=True, null=True, verbose_name="Image de couverture")
    favorite_postcard = models.ForeignKey('Postcard', on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='favorited_by', verbose_name="Carte préférée")
    website = models.URLField(blank=True, verbose_name="Site web")

    # Privacy settings
    show_activity = models.BooleanField(default=True, verbose_name="Afficher l'activité")
    show_connections = models.BooleanField(default=True, verbose_name="Afficher les connexions")
    allow_messages = models.BooleanField(default=True, verbose_name="Autoriser les messages")

    def generate_new_verification_code(self):
        """Generate and save a new verification code"""
        self.verification_code = generate_verification_code()
        self.verification_code_created_at = timezone.now()
        self.save(update_fields=['verification_code', 'verification_code_created_at'])
        return self.verification_code

    def is_verification_code_valid(self):
        """Check if verification code is still valid (30 minutes)"""
        if not self.verification_code or not self.verification_code_created_at:
            return False
        expiry_time = self.verification_code_created_at + datetime.timedelta(minutes=30)
        return timezone.now() < expiry_time

    def can_view_rare(self):
        return self.category in ['subscribed_verified', 'postman', 'viewer'] or self.is_staff

    def can_view_very_rare(self):
        return self.category in ['postman', 'viewer'] or self.is_staff

    def has_seen_intro_today(self):
        return self.last_intro_seen == timezone.now().date()

    def get_connections(self):
        """Get all users this user has exchanged postcards with"""
        from django.db.models import Q
        sent_to = SentPostcard.objects.filter(sender=self).values_list('recipient_id', flat=True)
        received_from = SentPostcard.objects.filter(recipient=self).values_list('sender_id', flat=True)
        connection_ids = set(sent_to) | set(received_from)
        connection_ids.discard(None)
        return CustomUser.objects.filter(id__in=connection_ids)

    def get_exchange_count_with(self, other_user):
        """Get number of postcards exchanged with another user"""
        sent = SentPostcard.objects.filter(sender=self, recipient=other_user).count()
        received = SentPostcard.objects.filter(sender=other_user, recipient=self).count()
        return sent + received

    def get_total_likes_given(self):
        return PostcardLike.objects.filter(user=self).count()

    def get_total_likes_received(self):
        """Likes on postcards this user sent"""
        return 0  # Can be expanded if needed

    def get_postcards_sent_count(self):
        return SentPostcard.objects.filter(sender=self).count()

    def get_postcards_received_count(self):
        return SentPostcard.objects.filter(recipient=self).count()

    def get_unread_postcards_count(self):
        return SentPostcard.objects.filter(recipient=self, is_read=False).count()

    def get_favorite_postcards(self):
        """All liked postcards (single unified like state, flag ignored)"""
        liked_ids = PostcardLike.objects.filter(user=self).values_list('postcard_id', flat=True)
        return Postcard.objects.filter(id__in=liked_ids)

    def get_favorite_animations(self):
        """Liked postcards that have an animation (unified like state)"""
        liked_ids = PostcardLike.objects.filter(user=self).values_list('postcard_id', flat=True)
        return Postcard.objects.filter(id__in=liked_ids, has_animation=True)

    def get_recent_activity(self, limit=20):
        """Get recent activity for this user"""
        return UserActivity.objects.filter(user=self).order_by('-timestamp')[:limit]

    def get_suggestions_count(self):
        return AnimationSuggestion.objects.filter(user=self).count()

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"


class UserConnection(models.Model):
    """Track epistolary relationships between users"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='connections_from')
    connected_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='connections_to')
    created_at = models.DateTimeField(auto_now_add=True)
    is_favorite = models.BooleanField(default=False, verbose_name="Favori")
    notes = models.TextField(blank=True, max_length=200, verbose_name="Notes personnelles")

    class Meta:
        unique_together = ['user', 'connected_to']
        verbose_name = "Connexion"
        verbose_name_plural = "Connexions"

    def __str__(self):
        return f"{self.user.username} -> {self.connected_to.username}"


class Postcard(models.Model):
    """
    Postcard model. Media derivative paths (vignette/grande/dos/zoom/animations)
    are cached on the row — populated by `rebuild_media_index` or
    `refresh_media_cache()` — so URL getters never touch the disk at request time.
    """
    RARITY_CHOICES = [
        ('common', 'Commune'),
        ('rare', 'Rare'),
        ('very_rare', 'Très Rare'),
    ]

    number = models.CharField(max_length=20, unique=True, verbose_name="Numéro", db_index=True)
    title = models.CharField(max_length=500, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    keywords = models.TextField(blank=True, verbose_name="Mots-clés", help_text="Séparés par des virgules")

    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common', verbose_name="Rareté")
    views_count = models.IntegerField(default=0, verbose_name="Nombre de vues")
    zoom_count = models.IntegerField(default=0, verbose_name="Nombre de zooms")
    likes_count = models.IntegerField(default=0, verbose_name="Nombre de likes")

    has_images = models.BooleanField(default=False, db_index=True, verbose_name="Images présentes")

    # Media cache — relative paths under MEDIA_ROOT, exact filenames as found on disk
    vignette_file = models.CharField(max_length=255, blank=True, default='')
    grande_file = models.CharField(max_length=255, blank=True, default='')
    dos_file = models.CharField(max_length=255, blank=True, default='')
    zoom_file = models.CharField(max_length=255, blank=True, default='')
    animation_files = models.JSONField(default=list, blank=True)
    has_animation = models.BooleanField(default=False, db_index=True, verbose_name="Animation présente")
    media_synced_at = models.DateTimeField(null=True, blank=True)

    # Accent-stripped lowercase of number + title + keywords, maintained on save
    search_blob = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_postcards'
    )

    class Meta:
        ordering = ['number']
        verbose_name = "Carte Postale"
        verbose_name_plural = "Cartes Postales"

    def __str__(self):
        return f"{self.number} - {self.title}"

    def get_padded_number(self):
        """Return the number padded to 6 digits"""
        num_str = ''.join(filter(str.isdigit, str(self.number)))
        if num_str:
            return num_str.zfill(6)
        return str(self.pk).zfill(6)

    def get_keywords_list(self):
        """Return keywords as a list"""
        return [k.strip() for k in self.keywords.split(',') if k.strip()]

    def build_search_blob(self):
        """Concatenated, accent-stripped, lowercased search text."""
        parts = [self.number, self.title, self.keywords]
        return normalize_search_text(' '.join(str(p) for p in parts if p))

    def save(self, *args, **kwargs):
        blob = self.build_search_blob()
        if blob != self.search_blob:
            self.search_blob = blob
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                update_fields = set(update_fields)
                update_fields.add('search_blob')
                kwargs['update_fields'] = list(update_fields)
        super().save(*args, **kwargs)

    # ---- Zero-I/O media URL getters (read the cached fields) ----

    def get_vignette_url(self):
        if self.vignette_file:
            return f'{settings.MEDIA_URL}{self.vignette_file}'
        return ''

    def get_grande_url(self):
        if self.grande_file:
            return f'{settings.MEDIA_URL}{self.grande_file}'
        return self.get_vignette_url()

    def get_dos_url(self):
        if self.dos_file:
            return f'{settings.MEDIA_URL}{self.dos_file}'
        return ''

    def get_zoom_url(self):
        if self.zoom_file:
            return f'{settings.MEDIA_URL}{self.zoom_file}'
        return self.get_grande_url()

    def get_animated_urls(self):
        return [f'{settings.MEDIA_URL}{path}' for path in (self.animation_files or [])]

    def has_vignette(self):
        return bool(self.vignette_file)

    def get_first_video_url(self):
        files = self.animation_files or []
        return f'{settings.MEDIA_URL}{files[0]}' if files else None

    @property
    def video_count(self):
        return len(self.animation_files or [])

    # ---- Media cache maintenance ----

    def refresh_media_cache(self, save=True):
        """
        Rescan the disk for THIS card only (used after an admin upload).
        Stores exact filenames as found, relative to MEDIA_ROOT.
        """
        media_root = Path(settings.MEDIA_ROOT)
        padded = self.get_padded_number()
        raw = str(self.number).strip()
        stems = [padded] if raw == padded else [padded, raw]

        def find_image(folder):
            base = media_root / 'postcards' / folder
            if not base.exists():
                return ''
            for stem in stems:
                for ext in MEDIA_IMAGE_EXTENSIONS:
                    candidate = base / f'{stem}{ext}'
                    if candidate.exists():
                        return f'postcards/{folder}/{candidate.name}'
            return ''

        self.vignette_file = find_image('Vignette')
        self.grande_file = find_image('Grande')
        self.dos_file = find_image('Dos')
        self.zoom_file = find_image('Zoom')

        animations = []
        animated_dir = media_root / 'animated_cp'
        if animated_dir.exists():
            for stem in stems:
                for ext in MEDIA_VIDEO_EXTENSIONS:
                    candidate = animated_dir / f'{stem}{ext}'
                    if candidate.exists():
                        animations.append(f'animated_cp/{candidate.name}')
                        break
                if animations:
                    break
            for i in range(20):
                found = False
                for stem in stems:
                    for ext in MEDIA_VIDEO_EXTENSIONS:
                        candidate = animated_dir / f'{stem}_{i}{ext}'
                        if candidate.exists():
                            animations.append(f'animated_cp/{candidate.name}')
                            found = True
                            break
                    if found:
                        break
                if not found:
                    break

        self.animation_files = animations
        self.has_animation = bool(animations)
        self.has_images = bool(self.vignette_file or self.grande_file)
        self.media_synced_at = timezone.now()

        if save:
            self.save(update_fields=[
                'vignette_file', 'grande_file', 'dos_file', 'zoom_file',
                'animation_files', 'has_animation', 'has_images', 'media_synced_at',
            ])
        return self

    def update_image_flags(self):
        """Historic name kept for the original admin flows — rescans this card."""
        self.refresh_media_cache(save=True)


class PostcardLike(models.Model):
    postcard = models.ForeignKey(Postcard, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_animated_like = models.BooleanField(default=False, verbose_name="Like pour animation")
    created_at = models.DateTimeField(auto_now_add=True)
    # New fields for enhanced tracking
    country = models.CharField(max_length=100, blank=True, verbose_name="Pays")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    device_type = models.CharField(max_length=50, blank=True, verbose_name="Type d'appareil")
    browser = models.CharField(max_length=100, blank=True, verbose_name="Navigateur")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")

    class Meta:
        verbose_name = "Like"
        verbose_name_plural = "Likes"
        ordering = ['-created_at']


# Add a new model for tracking hourly stats
class HourlyAnalytics(models.Model):
    """Pre-aggregated hourly analytics"""
    date = models.DateField()
    hour = models.IntegerField()  # 0-23
    page_views = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    searches = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)

    class Meta:
        unique_together = ['date', 'hour']
        ordering = ['-date', '-hour']
        verbose_name = "Analytique horaire"
        verbose_name_plural = "Analytiques horaires"

class AnimationSuggestion(models.Model):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('reviewed', 'Examiné'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
    ]
    postcard = models.ForeignKey(Postcard, on_delete=models.CASCADE, related_name='animation_suggestions')
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(verbose_name="Description de l'animation suggérée")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_suggestions'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Suggestion d'animation"
        verbose_name_plural = "Suggestions d'animation"


class Theme(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nom du thème")
    display_name = models.CharField(max_length=200, verbose_name="Nom affiché")
    postcards = models.ManyToManyField(Postcard, related_name='themes', blank=True)
    order = models.IntegerField(default=0, verbose_name="Ordre d'affichage")

    class Meta:
        ordering = ['order', 'display_name']
        verbose_name = "Thème"
        verbose_name_plural = "Thèmes"

    def __str__(self):
        return self.display_name


class ContactMessage(models.Model):
    message = models.TextField(verbose_name="Message")
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_read = models.BooleanField(default=False, verbose_name="Lu")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"


class SearchLog(models.Model):
    keyword = models.CharField(max_length=500, verbose_name="Mot-clé recherché")
    results_count = models.IntegerField(verbose_name="Nombre de résultats")
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Recherche"
        verbose_name_plural = "Historique des recherches"


class PageView(models.Model):
    page_name = models.CharField(max_length=100, verbose_name="Nom de la page")
    page_url = models.CharField(max_length=500, blank=True, verbose_name="URL de la page")
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    referrer = models.CharField(max_length=500, blank=True, verbose_name="Référent")
    country = models.CharField(max_length=100, blank=True, verbose_name="Pays")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    device_type = models.CharField(max_length=50, blank=True, verbose_name="Type d'appareil")
    browser = models.CharField(max_length=100, blank=True, verbose_name="Navigateur")
    os = models.CharField(max_length=100, blank=True, verbose_name="Système d'exploitation")

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Vue de page"
        verbose_name_plural = "Vues de pages"


class UserActivity(models.Model):
    ACTION_CHOICES = [
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('register', 'Inscription'),
        ('verify_email', 'Vérification email'),
        ('postcard_view', 'Vue carte postale'),
        ('postcard_zoom', 'Zoom carte postale'),
        ('postcard_like', 'Like carte postale'),
        ('postcard_unlike', 'Unlike carte postale'),
        ('animation_like', 'Like animation'),
        ('animation_suggest', 'Suggestion animation'),
        ('search', 'Recherche'),
        ('contact', 'Message de contact'),
        ('page_view', 'Vue de page'),
        ('postcard_sent', 'Carte envoyée'),
        ('postcard_received', 'Carte reçue'),
        ('profile_update', 'Mise à jour profil'),
        ('connection_add', 'Ajout connexion'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    related_postcard = models.ForeignKey(Postcard, null=True, blank=True, on_delete=models.SET_NULL)
    related_user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='related_activities')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activité utilisateur"
        verbose_name_plural = "Activités utilisateurs"

    def get_action_icon(self):
        icons = {
            'login': 'log-in',
            'logout': 'log-out',
            'register': 'user-plus',
            'verify_email': 'mail-check',
            'postcard_view': 'eye',
            'postcard_zoom': 'zoom-in',
            'postcard_like': 'heart',
            'postcard_unlike': 'heart-off',
            'animation_like': 'play-circle',
            'animation_suggest': 'lightbulb',
            'search': 'search',
            'contact': 'mail',
            'postcard_sent': 'send',
            'postcard_received': 'inbox',
            'profile_update': 'user-cog',
            'connection_add': 'user-plus',
        }
        return icons.get(self.action, 'activity')


class SystemLog(models.Model):
    LOG_LEVELS = [
        ('INFO', 'Information'),
        ('WARNING', 'Avertissement'),
        ('ERROR', 'Erreur'),
        ('CRITICAL', 'Critique'),
    ]
    level = models.CharField(max_length=10, choices=LOG_LEVELS, default='INFO')
    message = models.TextField()
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Log système"
        verbose_name_plural = "Logs système"


class IntroSeen(models.Model):
    session_key = models.CharField(max_length=100)
    date_seen = models.DateField(default=timezone.now)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Intro vue"
        verbose_name_plural = "Intros vues"
        unique_together = ['session_key', 'date_seen']


class SentPostcard(models.Model):
    VISIBILITY_CHOICES = [
        ('private', 'Privé - Destinataire uniquement'),
        ('public', 'Public - Visible par tous'),
    ]

    STAMP_CHOICES = [
        ('5c', '5 centimes - 44 caractères'),
        ('10c', '10 centimes - 55 caractères'),
    ]

    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_postcards')
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_postcards',
        null=True,
        blank=True
    )
    postcard = models.ForeignKey('Postcard', on_delete=models.SET_NULL, null=True, blank=True)
    custom_image_url = models.URLField(max_length=500, blank=True)
    message = models.TextField(max_length=55, verbose_name="Message")  # Max for 10c stamp
    stamp_type = models.CharField(max_length=10, choices=STAMP_CHOICES, default='10c', verbose_name="Type de timbre")
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    is_read = models.BooleanField(default=False)
    is_animated = models.BooleanField(default=False, verbose_name="Carte animée")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Carte postale envoyée"
        verbose_name_plural = "Cartes postales envoyées"

    def get_image_url(self):
        """Read the related card's cached media fields (zero disk I/O)."""
        if self.postcard:
            if self.is_animated:
                return self.postcard.get_first_video_url() or self.postcard.get_grande_url()
            return self.postcard.get_grande_url()
        return self.custom_image_url or ''

    def get_vignette_url(self):
        if self.postcard:
            return self.postcard.get_vignette_url()
        return self.custom_image_url or ''

    def get_video_url(self):
        """Get video URL if animated (cached field, zero disk I/O)"""
        if self.is_animated and self.postcard:
            return self.postcard.get_first_video_url()
        return None

    def get_max_characters(self):
        """Return max characters based on stamp type"""
        return 44 if self.stamp_type == '5c' else 55

    def get_sender_signature_url(self):
        """Get sender's signature image URL"""
        if self.sender.signature_image:
            return self.sender.signature_image.url
        return None


class PostcardComment(models.Model):
    sent_postcard = models.ForeignKey(SentPostcard, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"


# Analytics models
class VisitorSession(models.Model):
    """Track unique visitor sessions with detailed information"""
    session_key = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timezone = models.CharField(max_length=100, blank=True)
    isp = models.CharField(max_length=200, blank=True, verbose_name="Fournisseur d'accès")
    user_agent = models.TextField(blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    browser_version = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    screen_resolution = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=50, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    referrer_domain = models.CharField(max_length=200, blank=True)
    landing_page = models.CharField(max_length=500, blank=True)
    exit_page = models.CharField(max_length=500, blank=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    first_visit = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    page_views = models.IntegerField(default=0)
    total_time_spent = models.IntegerField(default=0, verbose_name="Temps passé (secondes)")
    is_bot = models.BooleanField(default=False)
    is_returning = models.BooleanField(default=False, verbose_name="Visiteur récurrent")

    # New fields for better tracking
    session_start = models.DateTimeField(null=True, blank=True)
    session_end = models.DateTimeField(null=True, blank=True)
    actions_count = models.IntegerField(default=0, verbose_name="Nombre d'actions")
    searches_count = models.IntegerField(default=0, verbose_name="Nombre de recherches")
    likes_count = models.IntegerField(default=0, verbose_name="Nombre de likes")

    class Meta:
        ordering = ['-last_activity']
        verbose_name = "Session visiteur"
        verbose_name_plural = "Sessions visiteurs"

    def calculate_duration(self):
        """Calculate actual session duration"""
        if self.session_start and self.session_end:
            delta = self.session_end - self.session_start
            return int(delta.total_seconds())
        elif self.session_start and self.last_activity:
            delta = self.last_activity - self.session_start
            return int(delta.total_seconds())
        return self.total_time_spent

    def save(self, *args, **kwargs):
        # Auto-set session_start on first save
        if not self.session_start:
            self.session_start = self.first_visit or timezone.now()
        super().save(*args, **kwargs)


class PostcardInteraction(models.Model):
    """Track detailed postcard interactions"""
    INTERACTION_TYPES = [
        ('view', 'Vue'),
        ('zoom', 'Zoom'),
        ('like', 'Like'),
        ('unlike', 'Unlike'),
        ('share', 'Partage'),
        ('download', 'Téléchargement'),
        ('animation_view', 'Vue animation'),
        ('flip', 'Retournement'),
    ]

    postcard = models.ForeignKey(Postcard, on_delete=models.CASCADE, related_name='interactions')
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    session = models.ForeignKey(VisitorSession, null=True, blank=True, on_delete=models.SET_NULL)
    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    duration = models.IntegerField(null=True, blank=True, verbose_name="Durée (secondes)")
    country = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Interaction carte"
        verbose_name_plural = "Interactions cartes"


class DailyAnalytics(models.Model):
    """Pre-aggregated daily analytics for faster dashboard loading"""
    date = models.DateField(unique=True)
    total_visits = models.IntegerField(default=0)
    unique_visitors = models.IntegerField(default=0)
    page_views = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    total_searches = models.IntegerField(default=0)
    total_likes = models.IntegerField(default=0)
    total_postcards_viewed = models.IntegerField(default=0)
    total_animations_viewed = models.IntegerField(default=0)
    total_zooms = models.IntegerField(default=0)
    total_messages = models.IntegerField(default=0)
    total_suggestions = models.IntegerField(default=0)
    bounce_rate = models.FloatField(default=0)
    avg_session_duration = models.IntegerField(default=0, verbose_name="Durée moyenne session (sec)")
    mobile_visits = models.IntegerField(default=0)
    tablet_visits = models.IntegerField(default=0)
    desktop_visits = models.IntegerField(default=0)
    top_countries = models.JSONField(default=dict, blank=True)
    top_referrers = models.JSONField(default=dict, blank=True)
    top_pages = models.JSONField(default=dict, blank=True)
    top_searches = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Analytique journalière"
        verbose_name_plural = "Analytiques journalières"


class RealTimeVisitor(models.Model):
    """Track real-time active visitors"""
    session_key = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    current_page = models.CharField(max_length=500, blank=True)
    page_title = models.CharField(max_length=200, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    last_activity = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_activity']
        verbose_name = "Visiteur en temps réel"
        verbose_name_plural = "Visiteurs en temps réel"


class IPLocation(models.Model):
    """Cache IP geolocation data to avoid repeated API calls"""
    ip_address = models.GenericIPAddressField(unique=True)
    country = models.CharField(max_length=100, blank=True)
    country_code = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timezone = models.CharField(max_length=100, blank=True)
    isp = models.CharField(max_length=200, blank=True)
    is_vpn = models.BooleanField(default=False)
    is_proxy = models.BooleanField(default=False)
    cached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Localisation IP"
        verbose_name_plural = "Localisations IP"