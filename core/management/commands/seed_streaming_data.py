from django.core.management.base import BaseCommand
from core.models import Movie, StreamingProvider, MovieStreamingAvailability

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Example: Manually add Netflix availability for popular movies
        netflix = StreamingProvider.objects.get(name="Netflix")
        amazon = StreamingProvider.objects.get(name="Amazon Prime Video")
        
        # Add some sample data (you'd do this for real movies in your DB)
        movies = Movie.objects.all()[:10]  # First 10 movies
        
        for movie in movies:
            # Manually add streaming availability
            MovieStreamingAvailability.objects.get_or_create(
                movie=movie,
                provider=netflix,
                defaults={
                    'monetization_type': 'flatrate',
                    'url': f'https://www.netflix.com/title/{movie.tmdb_id}'
                }
            )