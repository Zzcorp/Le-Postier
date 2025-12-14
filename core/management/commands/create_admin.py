# core/management/commands/create_admin.py
from django.core.management.base import BaseCommand
from core.models import CustomUser


class Command(BaseCommand):
    help = 'Create the admin superuser'

    def handle(self, *args, **options):
        username = 'samathey'
        email = 'sam@samathey.com'
        password = 'Elpatron78!'

        if CustomUser.objects.filter(username=username).exists():
            user = CustomUser.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.category = 'viewer'
            user.email_verified = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Updated superuser "{username}"'))
        else:
            CustomUser.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                category='viewer',
                email_verified=True
            )
            self.stdout.write(self.style.SUCCESS(f'✅ Created superuser "{username}"'))

        self.stdout.write(f'   Username: {username}')
        self.stdout.write(f'   Password: {password}')