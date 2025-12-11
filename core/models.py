# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
import os


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
    signature_image = models.ImageField(
        upload_to='signatures/',
        blank=True,
        null=True,
        verbose_name="Signature"
    )
    bio = models.TextField(blank=True, max_length=500, verbose_name="Biographie")

    def can_view_rare(self):
        return self.category in ['subscribed_verified', 'postman', 'viewer'] or self.is_staff

    def can_view_very_rare(self):
        return self.category in ['postman', 'viewer'] or self.is_staff

    def has_seen_intro_today(self):
        return self.last_intro_seen == timezone.now().date()

    def get_display_image(self):
        if self.signature_image:
            return self.signature_image.url
        return None

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"


def postcard_vignette_path(instance, filename):
    """Generate path for vignette: media/postcards/Vignette/000001.jpg"""
    num = str(instance.number).zfill(6)
    ext = os.path.splitext(filename)[1]
    return f'postcards/Vignette/{num}{ext}'


def postcard_grande_path(instance, filename):
    """Generate path for grande: media/postcards/Grande/000001.jpg"""
    num = str(instance.number).zfill(6)
    ext = os.path.splitext(filename)[1]
    return f'postcards/Grande/{num}{ext}'


def postcard_dos_path(instance, filename):
    """Generate path for dos: media/postcards/Dos/000001.jpg"""
    num = str(instance.number).zfill(6)
    ext = os.path.splitext(filename)[1]
    return f'postcards/Dos/{num}{ext}'


def postcard_zoom_path(instance, filename):
    """Generate path for zoom: media/postcards/Zoom/000001.jpg"""
    num = str(instance.number).zfill(6)
    ext = os.path.splitext(filename)[1]
    return f'postcards/Zoom/{num}{ext}'


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

    # Local image fields - stored on Render disk
    vignette_image = models.ImageField(
        upload_to=postcard_vignette_path,
        blank=True,
        null=True,
        verbose_name="Image Vignette"
    )
    grande_image = models.ImageField(
        upload_to=postcard_grande_path,
        blank=True,
        null=True,
        verbose_name="Image Grande"
    )
    dos_image = models.ImageField(
        upload_to=postcard_dos_path,
        blank=True,
        null=True,
        verbose_name="Image Dos"
    )
    zoom_image = models.ImageField(
        upload_to=postcard_zoom_path,
        blank=True,
        null=True,
        verbose_name="Image Zoom"
    )

    # Legacy URL fields - keep for backward compatibility but won't be used
    vignette_url = models.URLField(max_length=500, blank=True, verbose_name="URL Vignette (legacy)")
    grande_url = models.URLField(max_length=500, blank=True, verbose_name="URL Grande (legacy)")
    dos_url = models.URLField(max_length=500, blank=True, verbose_name="URL Dos (legacy)")
    zoom_url = models.URLField(max_length=500, blank=True, verbose_name="URL Zoom (legacy)")
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

    def get_vignette_url(self):
        """Get vignette URL - prioritize local file"""
        if self.vignette_image:
            return self.vignette_image.url
        return self.vignette_url or ''

    def get_grande_url(self):
        """Get grande URL - prioritize local file"""
        if self.grande_image:
            return self.grande_image.url
        return self.grande_url or ''

    def get_dos_url(self):
        """Get dos URL - prioritize local file"""
        if self.dos_image:
            return self.dos_image.url
        return self.dos_url or ''

    def get_zoom_url(self):
        """Get zoom URL - prioritize local file"""
        if self.zoom_image:
            return self.zoom_image.url
        return self.zoom_url or ''

    def get_animated_urls(self):
        """Return list of animated video URLs"""
        video_urls = []
        for video in self.videos.all():
            if video.video_file:
                video_urls.append(video.video_file.url)
            elif video.video_url:
                video_urls.append(video.video_url)
        if video_urls:
            return video_urls
        if self.animated_url:
            return [url.strip() for url in self.animated_url.split(',') if url.strip()]
        return []

    def has_animation(self):
        return self.videos.exists() or bool(self.animated_url)

    def get_first_video_url(self):
        first = self.videos.first()
        if first:
            if first.video_file:
                return first.video_file.url
            return first.video_url
        urls = self.get_animated_urls()
        return urls[0] if urls else None

    def video_count(self):
        count = self.videos.count()
        if count > 0:
            return count
        return len(self.get_animated_urls())


def animated_video_path(instance, filename):
    """Generate path for animated videos: media/animated_cp/000001_0.mp4"""
    num = str(instance.postcard.number).zfill(6)
    return f'animated_cp/{num}_{instance.order}{os.path.splitext(filename)[1]}'


class PostcardVideo(models.Model):
    postcard = models.ForeignKey(
        Postcard,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    video_url = models.URLField(max_length=500, blank=True, verbose_name="URL Vidéo (legacy)")
    video_file = models.FileField(
        upload_to=animated_video_path,
        blank=True,
        null=True,
        verbose_name="Vidéo Animée"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['postcard', 'order']
        verbose_name = "Vidéo animée"
        verbose_name_plural = "Vidéos animées"

    def __str__(self):
        return f"{self.postcard.number} - Video {self.order}"

    def get_video_url(self):
        """Get video URL - prioritize local file"""
        if self.video_file:
            return self.video_file.url
        return self.video_url or ''


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

    def __str__(self):
        return f"Like on {self.postcard.number}"


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


class SentPostcard(models.Model):
    VISIBILITY_CHOICES = [
        ('private', 'Privé - Destinataire uniquement'),
        ('public', 'Public - Visible par tous'),
    ]
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='sent_postcards'
    )
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='received_postcards',
        null=True,
        blank=True
    )
    postcard = models.ForeignKey(
        Postcard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    custom_image_url = models.URLField(max_length=500, blank=True)
    message = models.TextField(max_length=1000, verbose_name="Message")
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='private'
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Carte postale envoyée"
        verbose_name_plural = "Cartes postales envoyées"

    def __str__(self):
        if self.recipient:
            return f"De {self.sender.username} à {self.recipient.username}"
        return f"Carte publique de {self.sender.username}"

    def get_image_url(self):
        if self.postcard:
            return self.postcard.get_grande_url()
        return self.custom_image_url or ''


class PostcardComment(models.Model):
    sent_postcard = models.ForeignKey(
        SentPostcard,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE
    )
    message = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"