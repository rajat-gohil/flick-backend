from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Movie
from .models import Swipe
from .models import Session
from .models import Genre


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id','name']

class MovieSerializer(serializers.ModelSerializer):
    poster_url = serializers.SerializerMethodField()
    backdrop_url = serializers.SerializerMethodField()

    class Meta:
        model = Movie
        fields = [
            "id",
            "tmdb_id",
            "title",
            "overview",
            "release_date",
            "rating",
            "backdrop_url",
            "poster_url",
        ]
    
    def get_backdrop_url(self,obj):
        if obj.backdrop_path:
            return f"https://image.tmdb.org/t/p/w780{obj.backdrop_path}"
        return None
    def get_poster_url(self,obj):
        if obj.backdrop_path:
            return f"https://image.tmdb.org/t/p/w780{obj.poster_path}"
        return None

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user
    
class SwipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Swipe
        fields = ['id', 'session', 'movie', 'reaction']

    def validate_reaction(self, value):
        if value not in ['like', 'dislike']:
            raise serializers.ValidationError("Reaction must be 'like' or 'dislike'")
        return value

class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ['id', 'code', 'host', 'guest', 'is_active']
        read_only_fields = ['code', 'host', 'guest']

class SessionDetailSerializer(serializers.ModelSerializer):
    genre = serializers.SerializerMethodField()
    host_joined = serializers.SerializerMethodField()
    guest_joined = serializers.SerializerMethodField()
    ended = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            "id",
            "code",
            "genre",
            "host_joined",
            "guest_joined",
            "ended",
        ]

    def get_genre(self, obj):
        if obj.genre:
            return {
                "id": obj.genre.id,
                "name": obj.genre.name
            }
        return None

    def get_host_joined(self, obj):
        return obj.host is not None

    def get_guest_joined(self, obj):
        return obj.guest is not None

    def get_ended(self, obj):
        return obj.ended_at is not None
