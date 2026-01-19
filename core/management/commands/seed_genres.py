from django.core.management.base import BaseCommand
from core.models import Genre

GENRES = [
    (28, "Action"),
    (12, "Adventure"),
    (16, "Animation"),
    (35, "Comedy"),
    (80, "Crime"),
    (99, "Documentary"),
    (18, "Drama"),
    (10751, "Family"),
    (14, "Fantasy"),
    (36, "History"),
    (27, "Horror"),
    (10402, "Music"),
    (9648, "Mystery"),
    (10749, "Romance"),
    (878, "Science Fiction"),
    (10770, "TV Movie"),
    (53, "Thriller"),
    (10752, "War"),
    (37, "Western"),
]

class Command(BaseCommand):
    help = "Seed default TMDB genres"

    def handle(self, *args, **kwargs):
        created = 0

        for tmdb_id, name in GENRES:
            _, was_created = Genre.objects.get_or_create(
                tmdb_id=tmdb_id,
                defaults={"name": name}
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"Genres seeded successfully. New genres added: {created}")
        )
