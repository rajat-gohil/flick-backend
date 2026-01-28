from django.core.management.base import BaseCommand
from core.models import Genre
import requests
import os


class Command(BaseCommand):
    help = "Sync movie genres from TMDB"

    def handle(self, *args, **options):
        api_key = os.getenv("TMDB_API_KEY")

        if not api_key:
            self.stderr.write("TMDB_API_KEY not set")
            return

        url = "https://api.themoviedb.org/3/genre/movie/list"
        response = requests.get(
            url,
            params={
                "api_key": api_key,
                "language": "en-US",
            },
            timeout=10,
        )

        response.raise_for_status()
        data = response.json()

        created = 0

        for item in data.get("genres", []):
            _, was_created = Genre.objects.update_or_create(
                tmdb_id=item["id"],
                defaults={"name": item["name"]},
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Genres synced successfully. New genres created: {created}"
            )
        )
