# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid


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
    last_visit_date = models.DateField(null=True, blank=True, verbose_name="Dernière visite (date)")
    last_intro_seen = models.DateField(null=True, blank=True, verbose_name="Dernière intro vue")

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
    RARITY_CHOICES = [
        ('common', 'Commune'),
        ('rare', 'Rare'),
        ('very_rare', 'Très Rare'),
    ]

    number = models.CharField(max_length=20, unique=True, verbose_name="Numéro")
    title = models.CharField(max_length=500, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    keywords = models.TextField(blank=True, verbose_name="Mots-clés", help_text="Séparés par des virgules")

    # Store URLs instead of files - pointing to OVH
    vignette_url = models.URLField(max_length=500, blank=True, verbose_name="URL Vignette")
    grande_url = models.URLField(max_length=500, blank=True, verbose_name="URL Grande")
    dos_url = models.URLField(max_length=500, blank=True, verbose_name="URL Dos")
    zoom_url = models.URLField(max_length=500, blank=True, verbose_name="URL Zoom")
    # Legacy field - keep for backward compatibility, but use PostcardVideo model instead
    animated_url = models.TextField(max_length=2000, blank=True, verbose_name="URL Animation(s) (legacy)")

    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common', verbose_name="Rareté")

    views_count = models.IntegerField(default=0, verbose_name="Nombre de vues")
    zoom_count = models.IntegerField(default=0, verbose_name="Nombre de zooms")
    likes_count = models.IntegerField(default=0, verbose_name="Nombre de likes")

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

    def get_keywords_list(self):
        return [k.strip() for k in self.keywords.split(',') if k.strip()]

    def get_animated_urls(self):
        """Return list of animated video URLs from related PostcardVideo model"""
        video_urls = list(self.videos.values_list('video_url', flat=True))
        if video_urls:
            return video_urls
        # Fallback to legacy field
        if self.animated_url:
            return [url.strip() for url in self.animated_url.split(',') if url.strip()]
        return []

    def has_animation(self):
        """Check if postcard has any animation"""
        return self.videos.exists() or bool(self.animated_url)

    def get_first_video_url(self):
        """Get first video URL for preview"""
        first = self.videos.first()
        if first:
            return first.video_url
        # Fallback to legacy field
        urls = self.get_animated_urls()
        return urls[0] if urls else None

    def video_count(self):
        """Get number of videos"""
        count = self.videos.count()
        if count > 0:
            return count
        # Fallback to legacy field
        return len(self.get_animated_urls())

    # Properties to access images (for template compatibility)
    @property
    def vignette_image(self):
        return type('obj', (object,), {'url': self.vignette_url})()

    @property
    def grande_image(self):
        return type('obj', (object,), {'url': self.grande_url})()

    @property
    def dos_image(self):
        return type('obj', (object,), {'url': self.dos_url})()

    @property
    def zoom_image(self):
        return type('obj', (object,), {'url': self.zoom_url})()


class PostcardVideo(models.Model):
    """Store individual animated videos for postcards"""
    postcard = models.ForeignKey(
        Postcard,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    video_url = models.URLField(max_length=500, verbose_name="URL Vidéo")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['postcard', 'order']
        verbose_name = "Vidéo animée"
        verbose_name_plural = "Vidéos animées"

    def __str__(self):
        return f"{self.postcard.number} - Video {self.order}"


class PostcardLike(models.Model):
    """Track likes on postcards"""
    postcard = models.ForeignKey(Postcard, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_animated_like = models.BooleanField(default=False, verbose_name="Like pour animation")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Like"
        verbose_name_plural = "Likes"

    def __str__(self):
        return f"Like on {self.postcard.number}"


class AnimationSuggestion(models.Model):
    """Store user suggestions for animated postcards"""
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

    def __str__(self):
        return f"Suggestion for {self.postcard.number}"


class Theme(models.Model):
    name = models.CharField(max_length=200, unique=True, verbose_name="Nom du thème")
    display_name = models.CharField(max_length=200, verbose_name="Nom affiché")
    postcards = models.ManyToManyField(Postcard, related_name='themes', verbose_name="Cartes postales")
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

    def __str__(self):
        return f"Message du {self.created_at.strftime('%d/%m/%Y %H:%M')}"


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

    def __str__(self):
        return f"{self.keyword} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class PageView(models.Model):
    page_name = models.CharField(max_length=100, verbose_name="Nom de la page")
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.SET_NULL)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    session_key = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Vue de page"
        verbose_name_plural = "Vues de pages"

    def __str__(self):
        return f"{self.page_name} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"


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
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Activité utilisateur"
        verbose_name_plural = "Activités utilisateurs"

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()} - {self.timestamp}"


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

    def __str__(self):
        return f"{self.level} - {self.timestamp}"


class IntroSeen(models.Model):
    session_key = models.CharField(max_length=100)
    date_seen = models.DateField(default=timezone.now)
    user = models.ForeignKey(CustomUser, null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Intro vue"
        verbose_name_plural = "Intros vues"
        unique_together = ['session_key', 'date_seen']