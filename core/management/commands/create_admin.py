from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Create admin user with staff permissions'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Admin username')
        parser.add_argument('--email', type=str, help='Admin email')
        parser.add_argument('--password', type=str, help='Admin password')

    def handle(self, *args, **options):
        username = options['username'] or 'admin'
        email = options['email'] or 'admin@flick.com'
        password = options['password'] or 'admin123'

        # Check if user exists
        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            self.stdout.write(f'Found existing user: {username}')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(f'Created new user: {username}')

        # Ensure staff permissions
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully configured admin user: {username} with staff permissions'
            )
        )
