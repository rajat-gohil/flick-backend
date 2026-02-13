from django.core.management.base import BaseCommand
from core.models import StreamingProvider

class Command(BaseCommand):
    def handle(self, *args, **options):
        providers = [
            {"name": "Netflix", "website_url": "https://www.netflix.com", "country_code": "IN"},
            {"name": "Amazon Prime Video", "website_url": "https://www.primevideo.com", "country_code": "IN"},
            {"name": "Disney+", "website_url": "https://www.disneyplus.com", "country_code": "IN"},
            {"name": "Hotstar", "website_url": "https://www.hotstar.com", "country_code": "IN"},
            {"name": "SonyLIV", "website_url": "https://www.sonyliv.com", "country_code": "IN"},
            {"name": "MX Player", "website_url": "https://www.mxplayer.in", "country_code": "IN"},
        ]
        
        for provider_data in providers:
            provider, created = StreamingProvider.objects.get_or_create(
                name=provider_data["name"],
                defaults=provider_data
            )
            if created:
                print(f"Created provider: {provider.name}")
