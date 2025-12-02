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

    def can_view_rare(self):
        return self.category in ['subscribed_verified', 'postman', 'viewer'] or self.is_staff

    def can_view_very_rare(self):
        return self.category in ['postman', 'viewer'] or self.is_staff

    def has_seen_intro_today(self):
        return self.last_visit_date == timezone.now().date()

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
    animated_url = models.URLField(max_length=500, blank=True, verbose_name="URL Animation")

    rarity = models.CharField(max_length=20, choices=RARITY_CHOICES, default='common', verbose_name="Rareté")

    views_count = models.IntegerField(default=0, verbose_name="Nombre de vues")
    zoom_count = models.IntegerField(default=0, verbose_name="Nombre de zooms")

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
    session_key = models.CharField(max_length=100, unique=True)
    date_seen = models.DateField(default=timezone.now)

    class Meta:
        verbose_name = "Intro vue"
        verbose_name_plural = "Intros vues"