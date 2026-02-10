import random
import string
from datetime import timedelta

from django.utils import timezone
from django.db import IntegrityError
from django.db import models


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
from .serializers import MovieSerializer, RegisterSerializer, SwipeSerializer, SessionDetailSerializer
from .pagination import SwipeHistoryPagination
from .models import Genre
from .models import MovieExposure
from .models import SessionStats
from .models import UserTasteSignal
from .models import SessionChemistry
from .models import MovieTagRelation
from .models import MovieTag




# -------------------------------------------------------------------
# Recommendation shaping constants (Phase 2)
# -------------------------------------------------------------------

RECENT_EXPOSURE_COOLDOWN_MINUTES = 30
MAX_GLOBAL_EXPOSURE = 100
CANDIDATE_POOL_SIZE = 120
FINAL_DECK_SIZE = 40
MIN_DECK_SIZE = 16
MAX_DECK_SIZE = 50
INDIAN_LANGUAGES = ["hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]

# -------------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------------

def generate_session_code():
    """
    Generate a short, human-readable session code.
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def normalize_pair(user1, user2):
    """
    Ensures user pair ordering is consistent.
    """
    return (user1, user2) if user1.id < user2.id else (user2, user1)

def calculate_preference_score(movie, preferences):
    """
    Calculate how well a movie matches user preferences.
    Uses keyword matching AND release year filtering.
    """
    score = 0
    overview_lower = movie.overview.lower()
    title_lower = movie.title.lower()
    
    # Mood keywords (EXPANDED)
    mood_keywords = {
        "happy": ["comedy", "fun", "laugh", "joy", "light", "cheerful", "humorous", "hilarious", "amusing"],
        "intense": ["thriller", "suspense", "intense", "dark", "serious", "gripping", "tense", "dramatic"],
        "emotional": ["drama", "emotional", "moving", "heartfelt", "touching", "tear", "powerful", "profound"],
        "exciting": ["action", "adventure", "exciting", "fast-paced", "thrilling", "explosive", "dynamic"],
    }
    
    # Pace keywords (EXPANDED)
    pace_keywords = {
        "fast": ["action", "fast", "intense", "quick", "thrilling", "explosive", "adrenaline", "rush"],
        "slow": ["slow", "deliberate", "thoughtful", "contemplative", "meditative", "quiet", "introspective"],
        "balanced": ["balanced", "mix", "variety", "blend", "diverse"],
    }
    
    # Vibe keywords (EXPANDED)
    vibe_keywords = {
        "feel-good": ["uplifting", "inspiring", "heartwarming", "positive", "hopeful", "optimistic", "joyful"],
        "mind-bending": ["twist", "complex", "mystery", "puzzle", "psychological", "surreal", "enigmatic"],
        "escapist": ["fantasy", "adventure", "magical", "world", "epic", "mythical", "otherworldly"],
        "realistic": ["real", "authentic", "true", "based on", "documentary", "life", "actual"],
    }
    
    # Check moods (search in BOTH overview AND title)
    for mood in preferences.get("mood", []):
        keywords = mood_keywords.get(mood, [])
        for keyword in keywords:
            if keyword in overview_lower or keyword in title_lower:
                score += 5  # ✅ INCREASED from 3
                break
    
    # Check pace
    for pace in preferences.get("pace", []):
        keywords = pace_keywords.get(pace, [])
        for keyword in keywords:
            if keyword in overview_lower:
                score += 4  # ✅ INCREASED from 2
                break
    
    # Check vibe
    for vibe in preferences.get("vibe", []):
        keywords = vibe_keywords.get(vibe, [])
        for keyword in keywords:
            if keyword in overview_lower:
                score += 4  # ✅ INCREASED from 2
                break
    
    # ✅ NEW: Era/Decade filtering
    if movie.release_date:
        release_year = movie.release_date.year
        
        for era in preferences.get("era", []):
            if era == "classic" and release_year < 2000:
                score += 6
            elif era == "2000s" and 2000 <= release_year < 2010:
                score += 6
            elif era == "2010s" and 2010 <= release_year < 2020:
                score += 6
            elif era == "recent" and release_year >= 2020:
                score += 6
            elif era == "any":
                score += 2  # Small bonus for flexibility
    
    return score

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
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session = Session.objects.create(
            host=request.user,
            code=generate_session_code()
        )

        return Response(
            {
                "success": True,
                "id": session.id,
                "code": session.code,
            },
            status=status.HTTP_201_CREATED
        )

    
class SessionSetGenreView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        genre_id = request.data.get("genre_id")
        industry = request.data.get("industry")  # ✅ ADD THIS

        if not session_id or not genre_id or not industry:  # ✅ ADD industry check
            return Response(
                {"success": False, "error": "session_id, genre_id, and industry required"},
                status=400
            )

        # ✅ Validate industry
        if industry not in ["bollywood", "hollywood"]:
            return Response(
                {"success": False, "error": "Invalid industry"},
                status=400
            )

        try:
            session = Session.objects.get(id=session_id)
            genre = Genre.objects.get(id=genre_id)
        except (Session.DoesNotExist, Genre.DoesNotExist):
            return Response(
                {"success": False, "error": "Invalid session or genre"},
                status=404
            )

        if not session.host or request.user.id != session.host.id:
            return Response(
                {"success": False, "error": "Only host can set genre"},
                status=403
            )

        session.genre = genre
        session.industry = industry  # ✅ ADD THIS
        session.save(update_fields=["genre", "industry"])  # ✅ UPDATE THIS

        return Response(
            {
                "success": True,
                "session_id": session.id,
                "genre": {"id": genre.id, "name": genre.name},
                "industry": industry,  # ✅ ADD THIS
            },
            status=200
        )
    
class SessionSetPreferencesView(APIView):
    """
    Store user's mood/vibe preferences for the session.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        session_id = request.data.get("session_id")
        preferences = request.data.get("preferences")

        if not session_id or not preferences:
            return Response(
                {"success": False, "error": "session_id and preferences required"},
                status=400
            )

        try:
            session = Session.objects.get(id=session_id)
        except Session.DoesNotExist:
            return Response(
                {"success": False, "error": "Session not found"},
                status=404
            )

        if request.user not in [session.host, session.guest]:
            return Response(
                {"success": False, "error": "Not part of this session"},
                status=403
            )

        # Store preferences
        if request.user == session.host:
            session.host_preferences = preferences
        else:
            session.guest_preferences = preferences

        # Check if both submitted
        both_ready = False
        overlap_score = 0
        
        if session.host_preferences and session.guest_preferences:
            session.preferences_set = True
            both_ready = True
            
            # ✅ NEW: Calculate overlap
            host = session.host_preferences
            guest = session.guest_preferences
            
            # Count common preferences
            for key in ["mood", "pace", "vibe", "era"]:
                common = set(host.get(key, [])) & set(guest.get(key, []))
                overlap_score += len(common) * 10  # 10 points per match

        session.save()

        return Response(
            {
                "success": True,
                "both_ready": both_ready,
                "overlap_score": overlap_score,  # ✅ NEW: 0-100 compatibility score
            },
            status=200
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
        # --- Session Quality Score (Phase 2D) ---

        swipes = stats.total_swipes
        matches = stats.total_matches
        duration_minutes = (stats.duration_ms or 0) / 60000

        score = 0
        highlights = []

        # Match efficiency (core signal)
        if swipes > 0:
            match_ratio = matches / swipes
            score += min(int(match_ratio * 100), 40)

            if match_ratio > 0.2:
                highlights.append("Strong agreement")
            elif match_ratio < 0.05:
                highlights.append("Low alignment")

        # Absolute matches
        score += min(matches * 15, 30)
        if matches >= 2:
            highlights.append("Multiple matches")

        # Session depth
        if duration_minutes > 5:
            score += 10
            highlights.append("Good session flow")

        # Penalize dead sessions
        if swipes < 10:
            score -= 15
            highlights.append("Ended too early")

        # Clamp score
        stats.quality_score = max(0, min(score, 100))
        stats.highlights = highlights
        stats.save(update_fields=["quality_score", "highlights"])
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
        user_a, user_b = normalize_pair(session.host, session.guest)

        for tag in movie.tags.all():
            # Taste signal
            signal, _ = UserTasteSignal.objects.get_or_create(
                user=request.user,
                tag=tag
            )

            if reaction == Swipe.LIKE:
                signal.like_count += 1
            else:
                signal.dislike_count += 1

            signal.save(update_fields=["like_count", "dislike_count", "last_interacted_at"])

            # Session drift signal
            chemistry, _ = SessionChemistry.objects.get_or_create(
                user_a=user_a,
                user_b=user_b,
                tag=tag.name
            )

            chemistry.swipe_count += 1
            chemistry.save(update_fields=["swipe_count"])


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
                user_a, user_b = normalize_pair(session.host, session.guest)

                for tag in movie.tags.all():
                    chemistry, _ = SessionChemistry.objects.get_or_create(
                        user_a=user_a,
                        user_b=user_b,
                        tag=tag.name
                    )

                    chemistry.match_count += 1
                    chemistry.last_matched_at = timezone.now()
                    chemistry.save(update_fields=["match_count", "last_matched_at"])
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
                    "original_language": item.get("original_language"),
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

    def get(self, request):  # ✅ FIX: Proper indentation
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
        
        if request.user not in [session.host, session.guest]:
            return Response(
                {"success": False, "error": "Not part of this session"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not session.genre:
            return Response(
                {"success": False, "error": "Genre not selected yet"},
                status=400
            )

        # Get already swiped/matched movies
        swiped_movie_ids = Swipe.objects.filter(
            session=session
        ).values_list("movie_id", flat=True)

        matched_movie_ids = Match.objects.filter(
            session=session
        ).values_list("movie_id", flat=True)

        now = timezone.now()
        stats, _ = SessionStats.objects.get_or_create(session=session)

        swipes = stats.total_swipes
        matches = stats.total_matches

        # Adaptive deck sizing
        deck_size = FINAL_DECK_SIZE

        if swipes < 10:
            deck_size = MAX_DECK_SIZE  # 50 movies early on
        elif matches >= 2:
            deck_size = MIN_DECK_SIZE  # 16 movies if matching well
        elif swipes > 15 and matches == 0:  # ✅ CHANGED from 25
            # No matches after 15 swipes? Reduce variety, increase similarity
            deck_size = 20  # ✅ CHANGED from 10

        # Base candidate pool
        base_qs = Movie.objects.filter(genres=session.genre)

        # Industry filtering
        if session.industry == "bollywood":
            base_qs = base_qs.filter(original_language__in=INDIAN_LANGUAGES)
        elif session.industry == "hollywood":
            base_qs = base_qs.filter(original_language="en")

        candidate_ids = list(
            base_qs
            .exclude(id__in=swiped_movie_ids)
            .exclude(id__in=matched_movie_ids)
            .values_list("id", flat=True)
            .distinct()
        )[:CANDIDATE_POOL_SIZE]

        candidate_movies = Movie.objects.filter(id__in=candidate_ids)

        # ✅ NEW: Extract combined preferences
        combined_prefs = {}
        if session.host_preferences and session.guest_preferences:
            host_prefs = session.host_preferences
            guest_prefs = session.guest_preferences
            
            # Merge preferences (find common ground)
            combined_prefs = {
                "mood": list(set(host_prefs.get("mood", [])) & set(guest_prefs.get("mood", []))),
                "pace": list(set(host_prefs.get("pace", [])) & set(guest_prefs.get("pace", []))),
                "vibe": list(set(host_prefs.get("vibe", [])) & set(guest_prefs.get("vibe", []))),
            }
            
            # If no overlap, use union instead
            if not combined_prefs["mood"]:
                combined_prefs["mood"] = list(set(host_prefs.get("mood", [])) | set(guest_prefs.get("mood", [])))
            if not combined_prefs["pace"]:
                combined_prefs["pace"] = list(set(host_prefs.get("pace", [])) | set(guest_prefs.get("pace", [])))
            if not combined_prefs["vibe"]:
                combined_prefs["vibe"] = list(set(host_prefs.get("vibe", [])) | set(guest_prefs.get("vibe", [])))

        scored_movies = []

        for movie in candidate_movies:
            penalty = 0
            
            # ✅ NEW: Preference-based boosting
            if combined_prefs:
                boost = calculate_preference_score(movie, combined_prefs)
                penalty -= boost  # Negative penalty = higher priority

            if boost < 3:  # Minimum threshold
                continue  # Skip this movie entirely

            penalty -= boost

            # Existing taste bonus logic
            taste_bonus = 0
            for tag in movie.tags.all():
                try:
                    signal = UserTasteSignal.objects.get(user=request.user, tag=tag)
                    taste_bonus += (signal.like_count - signal.dislike_count)
                except UserTasteSignal.DoesNotExist:
                    pass
            penalty -= min(taste_bonus, 3)

            # Graph bonus logic
            graph_bonus = 0
            user_a, user_b = normalize_pair(session.host, session.guest)
            for tag in movie.tags.all():
                try:
                    chem = SessionChemistry.objects.get(
                        user_a=user_a, user_b=user_b, tag=tag.name
                    )
                    graph_bonus += chem.match_count * 2
                except SessionChemistry.DoesNotExist:
                    pass

                for rel in tag.outgoing_relations.all():
                    try:
                        neighbor = SessionChemistry.objects.get(
                            user_a=user_a, user_b=user_b, tag=rel.to_tag.name
                        )
                        graph_bonus += rel.weight * neighbor.match_count
                    except SessionChemistry.DoesNotExist:
                        pass
            penalty -= min(graph_bonus, 5)

            # Exposure penalties
            exposure, _ = MovieExposure.objects.get_or_create(movie=movie)
            recently_exposed = (
                exposure.last_exposed_at and
                (now - exposure.last_exposed_at).total_seconds() < 
                RECENT_EXPOSURE_COOLDOWN_MINUTES * 60  # ✅ FIX: Added < operator
            )

            if recently_exposed:
                penalty += 2
            if exposure.exposed_count >= MAX_GLOBAL_EXPOSURE:
                penalty += 3

            scored_movies.append((penalty, movie))

        # Sort and shuffle within penalty groups
        scored_movies.sort(key=lambda x: x[0])
        grouped = {}
        for penalty, movie in scored_movies:
            grouped.setdefault(penalty, []).append(movie)

        final_movies = []
        for penalty in sorted(grouped.keys()):
            random.shuffle(grouped[penalty])
            final_movies.extend(grouped[penalty])

        movies = final_movies[:deck_size]
        
        # Update exposure
        for movie in movies:
            try:
                exposure, _ = MovieExposure.objects.get_or_create(movie=movie)
                exposure.exposed_count += 1
                exposure.last_exposed_at = timezone.now()
                exposure.save(update_fields=["exposed_count", "last_exposed_at"])
            except Exception:
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
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        industry = request.query_params.get("industry")

        if industry not in ["bollywood", "hollywood"]:
            return Response(
                {"success": False, "error": "Valid industry required"},
                status=400
            )

        if industry == "bollywood":
            languages = ["hi", "ta", "te", "bn", "mr", "gu", "kn", "ml", "pa"]
        else:
            languages = ["en"]

        genres = Genre.objects.filter(
            movie__original_language__in=languages
        ).distinct().order_by("name")

        return Response(
            {
                "success": True,
                "genres": [{"id": g.id, "name": g.name} for g in genres]
            },
            status=200
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
    
class GenreSyncTMDBView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        from .services.tmdb import get_tmdb_genres

        created = 0
        updated = 0

        tmdb_genres = get_tmdb_genres()

        for g in tmdb_genres:
            genre, was_created = Genre.objects.update_or_create(
                tmdb_id=g["id"],
                defaults={
                    "name": g["name"],
                    # TEMP default – you will refine later
                    "industry": "hollywood",
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        return Response({
            "success": True,
            "created": created,
            "updated": updated,
        })
