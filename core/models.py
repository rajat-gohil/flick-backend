from django.db import models
from django.contrib.auth.models import User


# -------------------------------------------------
# Genre Model
# -------------------------------------------------

class Genre(models.Model):
    """
    TMDB genre reference.
    Stored once and reused across movies and sessions.
    """
    tmdb_id = models.IntegerField(unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# -------------------------------------------------
# Session Model
# -------------------------------------------------

class Session(models.Model):
    """
    A private swipe session between two users.
    Genre is fixed at creation time.
    """
    code = models.CharField(max_length=6, unique=True)

    host = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="hosted_sessions"
    )

    guest = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="joined_sessions"
    )

    # SINGLE genre per session (current product rule)
    genre = models.ForeignKey(
        Genre,
        on_delete=models.PROTECT,
        related_name="sessions"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def is_active(self):
        return self.ended_at is None

    def __str__(self):
        return f"Session {self.code} ({self.genre.name})"


# -------------------------------------------------
# Movie Model
# -------------------------------------------------

class Movie(models.Model):
    """
    Movie synced from TMDB.
    """
    tmdb_id = models.IntegerField(unique=True)
    title = models.CharField(max_length=255)
    overview = models.TextField(blank=True)
    poster_path = models.CharField(max_length=255, blank=True)
    backdrop_path = models.CharField(max_length=255, blank=True, null=True)
    release_date = models.DateField(null=True, blank=True)

    # Raw TMDB genre IDs (used during sync)
    tmdb_genre_ids = models.JSONField(default=list)

    # Relational genres (used by app logic)
    genres = models.ManyToManyField(Genre, blank=True)

    rating = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    streaming_providers = models.JSONField(default=dict, blank=True)




    def __str__(self):
        return self.title


# -------------------------------------------------
# Swipe Model
# -------------------------------------------------

class Swipe(models.Model):
    """
    A user's swipe (like/dislike) on a movie within a session.
    """
    LIKE = "like"
    DISLIKE = "dislike"

    REACTION_CHOICES = [
        (LIKE, "Like"),
        (DISLIKE, "Dislike"),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "session", "movie")

    def __str__(self):
        return f"{self.user.username} {self.reaction} {self.movie.title}"


# -------------------------------------------------
# Match Model
# -------------------------------------------------

class Match(models.Model):
    """
    Created when both users like the same movie in a session.
    """
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("session", "movie")
        constraints = [
            models.UniqueConstraint(
                fields=["session", "movie"],
                name="unique_match_per_movie_per_session"
            )
            ]

    def __str__(self):
        return f"Match: {self.movie.title} ({self.session.code})"
