# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings
import uuid
from pathlib import Path
import os


def get_media_root():
    """Get the correct media root path - always use persistent disk on Render"""
    from django.conf import settings
    import os
    from pathlib import Path

    if os.environ.get('RENDER', 'false').lower() == 'true' or Path('/var/data').exists():
        return Path('/var/data/media')
    return Path(settings.MEDIA_ROOT)


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
    bio = models.TextField(blank=True, max_length=500, verbose_name="Biographie")
    country = models.CharField(max_length=100, blank=True, verbose_name="Pays")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    registration_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP d'inscription")

    def can_view_rare(self):
        return self.category in ['subscribed_verified', 'postman', 'viewer'] or self.is_staff

    def can_view_very_rare(self):
        return self.category in ['postman', 'viewer'] or self.is_staff

    def has_seen_intro_today(self):
        return self.last_intro_seen == timezone.now().date()

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"


class Postcard(models.Model):
    """
    Postcard model - images are stored locally on disk.
    Image URLs are generated dynamically based on the postcard number.
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

    # Flag to indicate if images exist on disk
    has_images = models.BooleanField(default=False, verbose_name="Images présentes")

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

    def _find_local_image(self, folder):
        """
        Find image file in local media folder.
        Returns the URL if found, empty string otherwise.
        """
        from django.conf import settings

        # Use the correct media root
        media_root = get_media_root()
        padded = self.get_padded_number()
        base_path = media_root / 'postcards' / folder

        if not base_path.exists():
            return ''

        # Check for different extensions and case variations
        extensions = ['.jpg', '.jpeg', '.png', '.gif', '.JPG', '.JPEG', '.PNG', '.GIF']

        for ext in extensions:
            file_path = base_path / f'{padded}{ext}'
            if file_path.exists():
                return f'{settings.MEDIA_URL}postcards/{folder}/{padded}{ext}'

        # Also try with original number (without padding)
        original = str(self.number).strip()
        for ext in extensions:
            file_path = base_path / f'{original}{ext}'
            if file_path.exists():
                return f'{settings.MEDIA_URL}postcards/{folder}/{original}{ext}'

        return ''

    def get_vignette_url(self):
        """Get thumbnail image URL"""
        return self._find_local_image('Vignette')

    def get_grande_url(self):
        """Get large image URL"""
        url = self._find_local_image('Grande')
        return url if url else self.get_vignette_url()

    def get_dos_url(self):
        """Get back side image URL"""
        return self._find_local_image('Dos')

    def get_zoom_url(self):
        """Get zoom/high-res image URL"""
        url = self._find_local_image('Zoom')
        return url if url else self.get_grande_url()

    def get_animated_urls(self):
        """
        Find all animated video files for this postcard.
        Supports: 000001.mp4, 000001_0.mp4, 000001_1.mp4, etc.
        """
        from django.conf import settings

        video_urls = []
        padded = self.get_padded_number()

        # Use the correct media root
        media_root = get_media_root()
        animated_dir = media_root / 'animated_cp'

        if not animated_dir.exists():
            return video_urls

        # Check for single video: 000001.mp4
        for ext in ['.mp4', '.webm', '.MP4', '.WEBM']:
            single_file = animated_dir / f'{padded}{ext}'
            if single_file.exists():
                video_urls.append(f'{settings.MEDIA_URL}animated_cp/{padded}{ext}')
                break

        # Check for multiple videos: 000001_0.mp4, 000001_1.mp4, etc.
        for i in range(20):
            found = False
            for ext in ['.mp4', '.webm', '.MP4', '.WEBM']:
                multi_file = animated_dir / f'{padded}_{i}{ext}'
                if multi_file.exists():
                    video_urls.append(f'{settings.MEDIA_URL}animated_cp/{padded}_{i}{ext}')
                    found = True
                    break
            if not found and i > 0:
                break

        return video_urls

    def check_has_vignette(self):
        """Check if this postcard has a vignette image"""
        return bool(self.get_vignette_url())

    def check_has_animation(self):
        """Check if this postcard has any animations"""
        return len(self.get_animated_urls()) > 0

    def has_vignette(self):
        """Alias for check_has_vignette"""
        return self.check_has_vignette()

    def has_animation(self):
        """Alias for check_has_animation"""
        return self.check_has_animation()

    def get_first_video_url(self):
        """Get the first video URL if any"""
        urls = self.get_animated_urls()
        return urls[0] if urls else None

    def video_count(self):
        """Count number of videos"""
        return len(self.get_animated_urls())

    def update_image_flags(self):
        """Update has_images flag based on actual files"""
        self.has_images = self.check_has_vignette()
        self.save(update_fields=['has_images'])

    def debug_image_paths(self):
        """Debug image path resolution"""
        from django.conf import settings

        # Use the correct media root
        media_root = get_media_root()
        padded = self.get_padded_number()
        results = {
            'media_root': str(media_root),
            'padded_number': padded,
        }

        for folder in ['Vignette', 'Grande', 'Dos', 'Zoom']:
            base_path = media_root / 'postcards' / folder
            results[folder] = {
                'base_path': str(base_path),
                'exists': base_path.exists(),
                'files_checked': [],
                'found': None
            }

            for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                file_path = base_path / f'{padded}{ext}'
                results[folder]['files_checked'].append(str(file_path))
                if file_path.exists():
                    results[folder]['found'] = str(file_path)
                    break

        # Check animated
        animated_path = media_root / 'animated_cp'
        results['animated'] = {
            'base_path': str(animated_path),
            'exists': animated_path.exists(),
            'found': []
        }

        if animated_path.exists():
            for ext in ['.mp4', '.webm']:
                file_path = animated_path / f'{padded}{ext}'
                if file_path.exists():
                    results['animated']['found'].append(str(file_path))

        return results


class PostcardLike(models.Model):
    postcard = models.ForeignKey(Postcard, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_animated_like = models.BooleanField(default=False, verbose_name="Like pour animation")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Like"
        verbose_name_plural = "Likes"


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
        ('postcard_view', 'Vue carte postale'),
        ('postcard_zoom', 'Zoom carte postale'),
        ('postcard_like', 'Like carte postale'),
        ('animation_like', 'Like animation'),
        ('animation_suggest', 'Suggestion animation'),
        ('search', 'Recherche'),
        ('contact', 'Message de contact'),
        ('page_view', 'Vue de page'),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities', null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    session_key = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activité utilisateur"
        verbose_name_plural = "Activités utilisateurs"


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
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sent_postcards')
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_postcards',
        null=True,
        blank=True
    )
    postcard = models.ForeignKey(Postcard, on_delete=models.SET_NULL, null=True, blank=True)
    custom_image_url = models.URLField(max_length=500, blank=True)
    message = models.TextField(max_length=1000, verbose_name="Message")
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Carte postale envoyée"
        verbose_name_plural = "Cartes postales envoyées"

    def get_image_url(self):
        if self.postcard:
            return self.postcard.get_grande_url()
        return self.custom_image_url or ''


class PostcardComment(models.Model):
    sent_postcard = models.ForeignKey(SentPostcard, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"


# New models for enhanced analytics

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
    device_type = models.CharField(max_length=50, blank=True)  # mobile, tablet, desktop
    browser = models.CharField(max_length=100, blank=True)
    browser_version = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max)
    screen_resolution = models.CharField(max_length=50, blank=True)
    language = models.CharField(max_length=50, blank=True)
    referrer = models.CharField(max_length=500, blank=True)
    referrer_domain = models.CharField(max_length=200, blank=True)
    landing_page = models.CharField(max_length=500, blank=True)
    utm_source = models.CharField(max_length=100, blank=True)
    utm_medium = models.CharField(max_length=100, blank=True)
    utm_campaign = models.CharField(max_length=100, blank=True)
    first_visit = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    page_views = models.IntegerField(default=0)
    total_time_spent = models.IntegerField(default=0, verbose_name="Temps passé (secondes)")
    is_bot = models.BooleanField(default=False)

    class Meta:
        ordering = ['-last_activity']
        verbose_name = "Session visiteur"
        verbose_name_plural = "Sessions visiteurs"

    def __str__(self):
        return f"{self.ip_address} - {self.country} ({self.session_key[:8]})"


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

    # Top countries JSON field
    top_countries = models.JSONField(default=dict, blank=True)
    # Top referrers JSON field
    top_referrers = models.JSONField(default=dict, blank=True)
    # Top pages JSON field
    top_pages = models.JSONField(default=dict, blank=True)
    # Top searches JSON field
    top_searches = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "Analytique journalière"
        verbose_name_plural = "Analytiques journalières"

    def __str__(self):
        return f"Analytics for {self.date}"


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

    def __str__(self):
        return f"{self.ip_address} - {self.country}, {self.city}"