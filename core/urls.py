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
    GenreSyncTMDBView,
    SessionSetPreferencesView,
    )

urlpatterns = [
    # Change all these to have // prefix
    path('movies/', MovieListView.as_view(), name='movie-list'),
    path('movies/<int:pk>/', MovieDetailView.as_view(), name='movie-detail'),
    path('movies/create/', MovieCreateView.as_view(), name='movie-create'),
    path('movies/<int:pk>/update/', MovieUpdateView.as_view(), name='movie-update'),
    path('movies/<int:pk>/delete/', MovieDeleteView.as_view(), name='movie-delete'),
    path("movies/sync-tmdb/", MovieSyncTMDBView.as_view(), name="movie-sync-tmdb"),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('swipes/', SwipeCreateView.as_view(), name='swipe-create'),
    path('sessions/create/', SessionCreateView.as_view(), name='session-create'),  # ← Add //
    path('sessions/join/', SessionJoinView.as_view(), name='session-join'),
    path("sessions/end/", SessionEndView.as_view(), name="session-end"),
    path("matches/", MatchListView.as_view(), name="match-list"),
    path("swipes/undo/", SwipeUndoView.as_view(), name="swipe-undo"),
    path("swipes/history/", SwipeHistoryView.as_view(), name="swipe-history"),
    path("recommendations/", RecommendationView.as_view(), name="recommendations"),
    path("genres/", GenreListView.as_view(), name="genre-list"),  # ← Add //
    path("sessions/<int:session_id>/", SessionDetailView.as_view(), name="session-detail"),
    path("sessions/status/", SessionStatusView.as_view(), name="session-status"),
    path("sessions/genre/", SessionSetGenreView.as_view(), name="session-genre"),
    path("genres/sync-tmdb/", GenreSyncTMDBView.as_view()),
    path('sessions/preferences/', SessionSetPreferencesView.as_view()),

]