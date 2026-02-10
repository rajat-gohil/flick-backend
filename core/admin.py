from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import Movie, Genre, Session, Swipe, Match

# Register your models here
@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'tmdb_id', 'release_date', 'rating', 'original_language')
    list_filter = ('original_language', 'genres', 'release_date')
    search_fields = ('title', 'tmdb_id')
    filter_horizontal = ('genres',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'tmdb_id', 'industry')
    list_filter = ('industry',)
    search_fields = ('name', 'tmdb_id')

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('code', 'host', 'guest', 'genre', 'industry', 'created_at', 'ended_at')
    list_filter = ('industry', 'created_at', 'ended_at')
    search_fields = ('code', 'host__username', 'guest__username')
    readonly_fields = ('created_at', 'ended_at')

@admin.register(Swipe)
class SwipeAdmin(admin.ModelAdmin):
    list_display = ('user', 'session', 'movie', 'reaction', 'created_at')
    list_filter = ('reaction', 'created_at', 'session__genre')
    search_fields = ('user__username', 'movie__title')
    readonly_fields = ('created_at',)

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('session', 'movie', 'created_at')
    list_filter = ('created_at', 'session__genre')
    search_fields = ('movie__title', 'session__code')
    readonly_fields = ('created_at',)

# Extend UserAdmin to show custom fields
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

# Customize admin site headers
admin.site.site_header = 'Flick Administration'
admin.site.site_title = 'Flick Admin'
admin.site.index_title = 'Flick Administration Dashboard'
