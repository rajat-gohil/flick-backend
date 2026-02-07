from django.urls import path
from django.contrib import admin
from django.urls import path
from .views import (
    MovieListView,
    MovieDetailView,
    MovieCreateView,
    MovieUpdateView,
    MovieDeleteView,
    RegisterView,
    LoginView,
    SwipeCreateView,
    SessionCreateView, 
    SessionJoinView,
    MatchListView,
    SwipeUndoView,
    SwipeHistoryView,
    SessionEndView,
    MovieSyncTMDBView,
    RecommendationView,
    GenreListView,
    SessionDetailView,
    SessionStatusView,
    SessionSetGenreView,
    )

urlpatterns = [
    # Change all these to have /api/ prefix
    path('api/movies/', MovieListView.as_view(), name='movie-list'),
    path('api/movies/<int:pk>/', MovieDetailView.as_view(), name='movie-detail'),
    path('api/movies/create/', MovieCreateView.as_view(), name='movie-create'),
    path('api/movies/<int:pk>/update/', MovieUpdateView.as_view(), name='movie-update'),
    path('api/movies/<int:pk>/delete/', MovieDeleteView.as_view(), name='movie-delete'),
    path("api/movies/sync-tmdb/", MovieSyncTMDBView.as_view(), name="movie-sync-tmdb"),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/swipes/', SwipeCreateView.as_view(), name='swipe-create'),
    path('api/sessions/create/', SessionCreateView.as_view(), name='session-create'),  # ← Add /api/
    path('api/sessions/join/', SessionJoinView.as_view(), name='session-join'),
    path("api/sessions/end/", SessionEndView.as_view(), name="session-end"),
    path("api/matches/", MatchListView.as_view(), name="match-list"),
    path("api/swipes/undo/", SwipeUndoView.as_view(), name="swipe-undo"),
    path("api/swipes/history/", SwipeHistoryView.as_view(), name="swipe-history"),
    path("api/recommendations/", RecommendationView.as_view(), name="recommendations"),
    path("api/genres/", GenreListView.as_view(), name="genre-list"),  # ← Add /api/
    path("api/sessions/<int:session_id>/", SessionDetailView.as_view(), name="session-detail"),
    path("api/sessions/status/", SessionStatusView.as_view(), name="session-status"),
    path("api/sessions/genre/", SessionSetGenreView.as_view(), name="session-genre"),
]