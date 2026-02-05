import random
import string
from datetime import timedelta

from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Count, Q

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework import status


from .models import Movie, Swipe, Match, Session, Genre
from .serializers import MovieSerializer, RegisterSerializer, SwipeSerializer, GenreSerializer, SessionDetailSerializer
from .pagination import SwipeHistoryPagination
from .models import Genre
from .models import MovieExposure
from .models import SessionStats

# -------------------------------------------------------------------
# Recommendation shaping constants (Phase 2)
# -------------------------------------------------------------------

RECENT_EXPOSURE_COOLDOWN_MINUTES = 30
MAX_GLOBAL_EXPOSURE = 50
CANDIDATE_POOL_SIZE = 60
FINAL_DECK_SIZE = 20

# -------------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------------

def generate_session_code():
    """
    Generate a short, human-readable session code.
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# -------------------------------------------------------------------
# Movie APIs
# -------------------------------------------------------------------

class MovieListView(generics.ListAPIView):
    """
    Public list of all movies.
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer


class MovieDetailView(generics.RetrieveAPIView):
    """
    Retrieve details for a single movie.
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer


class MovieCreateView(generics.CreateAPIView):
    """
    Create a new movie (authentication required).
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class MovieUpdateView(generics.UpdateAPIView):
    """
    Update an existing movie.
    """
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class MovieDeleteView(generics.DestroyAPIView):
    """
    Delete a movie.
    """
    queryset = Movie.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


# -------------------------------------------------------------------
# Authentication APIs
# -------------------------------------------------------------------

class RegisterView(APIView):
    """
    Register a new user account.
    """
    permission_classes = [AllowAny]
    authetication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(
            {"success": True, "message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )


class LoginView(ObtainAuthToken):
    """
    Authenticate a user and return a token.
    """
    permission_classes = [AllowAny]
    authetication_classes = []

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        token = Token.objects.get(key=response.data["token"])

        return Response({
            "success": True,
            "token": token.key,
            "user_id": token.user.id,
            "username": token.user.username,
        })


# -------------------------------------------------------------------
# Session APIs
# -------------------------------------------------------------------

class SessionCreateView(APIView):
    """
    Create a new session.
    A valid genre_id is required and stored on the session.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        genre_id = request.data.get("genre_id")

        if not genre_id:
            return Response(
                {
                    "success": False,
                    "error": "genre_id is required"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            genre = Genre.objects.get(id=genre_id)
        except Genre.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "error": "Invalid genre_id"
                },
                status=status.HTTP_404_NOT_FOUND
            )

        session = Session.objects.create(
            host=request.user,
            genre=genre,
            code=generate_session_code()
        )

        return Response(
            {
                "success": True,
                "session_id": session.id,
                "code": session.code,
                "genre": {
                    "id": genre.id,
                    "name": genre.name
                }
            },
            status=status.HTTP_201_CREATED
        )

class SessionJoinView(APIView):
    """
    Join an existing session using a session code.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")

        if not code:
            return Response(
                {"success": False, "error": "Session code required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = Session.objects.get(code=code)
        except Session.DoesNotExist:
            return Response(
                {"success": False, "error": "Invalid session code"},
                status=status.HTTP_404_NOT_FOUND
            )

        if session.host == request.user:
            return Response(
                {"success": False, "error": "Host cannot join own session"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if session.guest:
            return Response(
                {"success": False, "error": "Session already full"},
                status=status.HTTP_409_CONFLICT
            )

        session.guest = request.user
        session.save()

        return Response(
            {"success": True, "message": "Joined session", "session_id": session.id},
            status=status.HTTP_200_OK
        )


class SessionEndView(APIView):
    """
    End an active session manually.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")

        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response(
                {"success": False, "error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user not in [session.host, session.guest]:
            return Response(
                {"success": False, "error": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN
            )

        session.ended_at = timezone.now()
        session.save()
        stats, _ = SessionStats.objects.get_or_create(session=session)

        if session.created_at:
            duration = timezone.now() - session.created_at
            stats.duration_ms = int(duration.total_seconds() * 1000)

        stats.ended_by = "user"
        stats.save(update_fields=["duration_ms", "ended_by"])

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"session_{session.id}",
            {
                "type": "session_ended_event",
                "session_id": session.id,
            }
        )

        return Response(
            {"success": True, "message": "Session ended"},
            status=status.HTTP_200_OK
        )


# -------------------------------------------------------------------
# Swipe APIs
# -------------------------------------------------------------------

class SwipeCreateView(APIView):
    """
    Records a swipe for a movie inside a session.
    - Enforces session rules
    - Prevents duplicate swipes
    - Detects matches
    - Emits WebSocket event on match
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SwipeSerializer(data=request.data)

        # 1. Validate request payload
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        session = serializer.validated_data["session"]
        movie = serializer.validated_data["movie"]
        reaction = serializer.validated_data["reaction"]

        # 2. Session state checks
        if session.ended_at:
            return Response(
                {"success": False, "error": "Session has ended"},
                status=status.HTTP_403_FORBIDDEN
            )

        if not session.host or not session.guest:
            return Response(
                {"success": False, "error": "Session is not ready yet"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Membership check
        if request.user not in (session.host, session.guest):
            return Response(
                {"success": False, "error": "You are not part of this session"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 4. Block swipes if movie already matched
        if Match.objects.filter(session=session, movie=movie).exists():
            return Response(
                {"success": False, "error": "This movie is already matched"},
                status=status.HTTP_409_CONFLICT
            )

        # 5. Create swipe (unique constraint enforced at DB level)
        try:
            swipe = Swipe.objects.create(
                user=request.user,
                session=session,
                movie=movie,
                reaction=reaction
            )
            stats, _ = SessionStats.objects.get_or_create(session=session)
            stats.total_swipes += 1
            stats.save(update_fields=["total_swipes"])
            # Notify partner that a swipe happened
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"session_{session.id}",
                {
                    "type": "swipe_event",
                    "user_id": request.user.id,
                }
            )
        except IntegrityError:
            return Response(
                {"success": False, "error": "Already swiped on this movie"},
                status=status.HTTP_409_CONFLICT
            )

        # 6. Match detection
        match_created = False

        if reaction == Swipe.LIKE:
            liked_users = Swipe.objects.filter(
                session=session,
                movie=movie,
                reaction=Swipe.LIKE
            ).values_list("user_id", flat=True)

            if len(set(liked_users)) == 2:
                Match.objects.create(session=session, movie=movie)
                match_created = True
                stats, _ = SessionStats.objects.get_or_create(session=session)
                stats.total_matches += 1
                stats.save(update_fields=["total_matches"])


                # Emit WebSocket event
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"session_{session.id}",
                    {
                        "type": "match_event",
                        "session_id": session.id,
                        "movie_id": movie.id,
                        "movie_title": movie.title,
                    }
                )

        # 7. Final response
        return Response(
            {
                "success": True,
                "match": match_created,
                "ask_to_end": match_created,
                "message": "It's a match!" if match_created else "Swipe recorded",
                "reaction": reaction,
            },
            status=status.HTTP_201_CREATED
        )




class SwipeUndoView(APIView):
    """
    Undo a swipe within a 10-second window if no match exists.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        session_id = request.data.get("session_id")
        movie_id = request.data.get("movie_id")

        if not session_id or not movie_id:
            return Response(
                {"success": False, "error": "session_id and movie_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            swipe = Swipe.objects.get(
                user=request.user,
                session_id=session_id,
                movie_id=movie_id
            )
        except Swipe.DoesNotExist:
            return Response(
                {"success": False, "error": "Swipe not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if Match.objects.filter(session_id=session_id, movie_id=movie_id).exists():
            return Response(
                {"success": False, "error": "Cannot undo after match"},
                status=status.HTTP_409_CONFLICT
            )

        if timezone.now() - swipe.created_at > timedelta(seconds=10):
            return Response(
                {"success": False, "error": "Undo window expired"},
                status=status.HTTP_403_FORBIDDEN
            )

        swipe.delete()
        return Response(
            {"success": True, "message": "Swipe undone"},
            status=status.HTTP_200_OK
        )


class SwipeHistoryView(APIView):
    """
    Paginated swipe history for the logged-in user.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = SwipeHistoryPagination

    def get(self, request):
        session_id = request.query_params.get("session_id")

        swipes = Swipe.objects.filter(
            user=request.user
        ).select_related(
            "movie", "session"
        ).order_by("-created_at")

        if session_id:
            swipes = swipes.filter(session_id=session_id)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(swipes, request)

        data = [
            {
                "session_id": swipe.session.id,
                "movie_id": swipe.movie.id,
                "movie_title": swipe.movie.title,
                "reaction": swipe.reaction,
                "swiped_at": swipe.created_at,
            }
            for swipe in page
        ]

        return paginator.get_paginated_response({
            "success": True,
            "swipes": data,
        })


# -------------------------------------------------------------------
# Match APIs
# -------------------------------------------------------------------

class MatchListView(APIView):
    """
    List match history for the logged-in user.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        matches = Match.objects.filter(
            session__host=user
        ) | Match.objects.filter(
            session__guest=user
        )

        matches = matches.select_related(
            "movie", "session"
        ).order_by("-created_at")

        data = [
            {
                "session_id": match.session.id,
                "movie_id": match.movie.id,
                "movie_title": match.movie.title,
                "matched_at": match.created_at,
            }
            for match in matches
        ]

        return Response(
            {"success": True, "matches": data},
            status=status.HTTP_200_OK
        )

class MovieSyncTMDBView(APIView):
    """
    Sync popular movies from TMDB into local database.
    Safe to run multiple times.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from .services.tmdb import get_popular_movies
        from .models import Genre

        movies_created = 0
        tmdb_data = get_popular_movies(page=1)

        for item in tmdb_data.get("results", []):
            movie, created = Movie.objects.update_or_create(
                tmdb_id=item["id"],
                defaults={
                    "title": item["title"],
                    "overview": item.get("overview", ""),
                    "poster_path": item.get("poster_path", ""),
                    "backdrop_path": item.get("backdrop_path", ""),
                    "release_date": item.get("release_date") or None,
                    "rating": item.get("vote_average"),
                }
            )

            # ✅ Correct genre linking
            tmdb_genre_ids = item.get("genre_ids", [])
            genre_objects = Genre.objects.filter(tmdb_id__in=tmdb_genre_ids)

            movie.genres.set(genre_objects)

            if created:
                movies_created += 1

        return Response(
            {
                "success": True,
                "created": movies_created,
                "total_fetched": len(tmdb_data.get("results", [])),
            },
            status=status.HTTP_200_OK
        )

class RecommendationView(APIView):
    """
    Returns swipeable movie recommendations
    filtered by the session's selected genre.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get("session_id")

        if not session_id:
            return Response(
                {"success": False, "error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = Session.objects.select_related("genre").get(id=session_id)
        except Session.DoesNotExist:
            return Response(
                {"success": False, "error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # User must be part of session
        if request.user not in [session.host, session.guest]:
            return Response(
                {"success": False, "error": "Not part of this session"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get already swiped movie IDs
        swiped_movie_ids = Swipe.objects.filter(
            session=session
        ).values_list("movie_id", flat=True)

        # Get already matched movie IDs
        matched_movie_ids = Match.objects.filter(
            session=session
        ).values_list("movie_id", flat=True)

        now = timezone.now()

        # Base candidate pool
        candidate_ids = list(
            Movie.objects.filter(
                genres=session.genre
            )
            .exclude(id__in=swiped_movie_ids)
            .exclude(id__in=matched_movie_ids)
            .values_list("id", flat=True)
            .distinct()
        )[:CANDIDATE_POOL_SIZE]

        candidate_movies = Movie.objects.filter(id__in=candidate_ids)


        scored_movies = []

        for movie in candidate_movies:
            exposure, _ = MovieExposure.objects.get_or_create(movie=movie)

            # Penalize recently exposed movies
            recently_exposed = (
                exposure.last_exposed_at and
                (now - exposure.last_exposed_at).total_seconds() <
                RECENT_EXPOSURE_COOLDOWN_MINUTES * 60
            )

            # Penalize globally over-exposed movies
            over_exposed = exposure.exposed_count >= MAX_GLOBAL_EXPOSURE

            # Soft score (lower is worse)
            penalty = 0
            if recently_exposed:
                penalty += 2
            if over_exposed:
                penalty += 3

            scored_movies.append((penalty, movie))

        # Sort by penalty, then shuffle inside penalty groups
        scored_movies.sort(key=lambda x: x[0])

        grouped = {}
        for penalty, movie in scored_movies:
            grouped.setdefault(penalty, []).append(movie)

        final_movies = []
        for penalty in sorted(grouped.keys()):
            random.shuffle(grouped[penalty])
            final_movies.extend(grouped[penalty])

        movies = final_movies[:FINAL_DECK_SIZE]
        for movie in movies:
            try:
                exposure, _ = MovieExposure.objects.get_or_create(movie=movie)
                exposure.exposed_count += 1
                exposure.last_exposed_at = timezone.now()
                exposure.save(update_fields=["exposed_count", "last_exposed_at"])
            except Exception:
                # Never break recommendations due to analytics
                pass

        serializer = MovieSerializer(movies, many=True)

        return Response(
            {
                "success": True,
                "session_id": session.id,
                "genre": session.genre.name,
                "movies": serializer.data
            },
            status=status.HTTP_200_OK
        )

class GenreListView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        genres = Genre.objects.all().order_by('name')

        data = [
            {'id': genre.id, 'name':genre.name}
            for genre in genres
        ]

        return Response(
            {'success': True, 'genres': data},
            status=status.HTTP_200_OK
        )
    
class SessionGenreSelectView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        genre_ids = request.data.get("genre_ids", [])

        if not session_id or not genre_ids:
            return Response(
                {"success": False, "error": "session_id and genre_ids required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response(
                {"success": False, "error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user not in [session.host, session.guest]:
            return Response(
                {"success": False, "error": "Not part of this session"},
                status=status.HTTP_403_FORBIDDEN
            )

        genres = Genre.objects.filter(id__in=genre_ids)

        # Save selection based on role
        if request.user == session.host:
            session.host_selected_genres.set(genres)
        else:
            session.guest_selected_genres.set(genres)

        # Check if both users have selected
        if session.host_selected_genres.exists() and session.guest_selected_genres.exists():
            agreed_genres = session.host_selected_genres.filter(
                id__in=session.guest_selected_genres.values_list("id", flat=True)
            )

            if not agreed_genres.exists():
                return Response(
                    {
                        "success": False,
                        "error": "No common genres. Please reselect."
                    },
                    status=status.HTTP_409_CONFLICT
                )

            session.selected_genres.set(agreed_genres)

            return Response(
                {
                    "success": True,
                    "agreed": True,
                    "message": "Genres matched",
                    "genres": list(agreed_genres.values("id", "name"))
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "success": True,
                "agreed": False,
                "message": "Waiting for other user to select genres"
            },
            status=status.HTTP_200_OK
        )
    
class SessionDetailView(APIView):
    """
    Get session state for frontend polling.
    """

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response(
                {"success": False, "error": "Session not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if request.user not in [session.host, session.guest]:
            return Response(
                {"success": False, "error": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SessionDetailSerializer(session)
        return Response(
            {"success": True, "session": serializer.data},
            status=status.HTTP_200_OK
        )

class SessionStatusView(APIView):
    """
    Public session status lookup by code.
    Used before joining a session.
    """

    def get(self, request):
        code = request.query_params.get("code")

        if not code:
            return Response(
                {"success": False, "error": "Session code required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            session = Session.objects.get(code=code)
        except Session.DoesNotExist:
            return Response(
                {"success": False, "exists": False},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {
                "success": True,
                "exists": True,
                "session": {
                    "id": session.id,
                    "host_joined": True,
                    "guest_joined": session.guest is not None,
                    "ended": session.ended_at is not None,
                    "genre": {
                        "id": session.genre.id,
                        "name": session.genre.name
                    } if session.genre else None,
                },
            },
            status=status.HTTP_200_OK
        )
    
