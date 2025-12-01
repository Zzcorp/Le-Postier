from django.core.management.base import BaseCommand
from core.models import CustomUser


class Command(BaseCommand):
    help = 'Create the initial admin user'

    def handle(self, *args, **options):
        if not CustomUser.objects.filter(username='samathey').exists():
            CustomUser.objects.create_superuser(
                username='samathey',
                email='sam@samathey.com',
                password='Elpatron78!',
                category='viewer',
                email_verified=True
            )
            self.stdout.write(self.style.SUCCESS('Successfully created admin user'))
        else:
            self.stdout.write(self.style.WARNING('Admin user already exists'))