from django.core.management.base import BaseCommand
from core.models import Movie, Genre
from core.services.tmdb import get_popular_movies



class Command(BaseCommand):
    help = "Sync popular movies from TMDB"

    def handle(self, *args, **options):
        movies_created = 0

        # Fetch multiple pages for a larger pool
        for page in range(1, 9999):  # pages 1–5
            tmdb_data = get_popular_movies(page=page)

            for item in tmdb_data.get("results", []):
                movie, created = Movie.objects.update_or_create(
                    tmdb_id=item["id"],
                    defaults={
                        "title": item["title"],
                        "overview": item.get("overview", ""),
                        "poster_path": item.get("poster_path") or "",
                        "backdrop_path": item.get("backdrop_path") or "",
                        "release_date": item.get("release_date") or None,
                        "rating": item.get("vote_average"),
                    }
                )

                                # Link genres
                tmdb_genre_ids = item.get("genre_ids", [])
                genre_objects = Genre.objects.filter(tmdb_id__in=tmdb_genre_ids)
                movie.genres.set(genre_objects)

                if created:
                    movies_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Movies synced successfully. New movies created: {movies_created}"
            )
        )
