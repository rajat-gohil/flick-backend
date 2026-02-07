import httpx
from django.conf import settings

BASE_URL = "https://api.themoviedb.org/3"

TIMEOUT = httpx.Timeout(10.0, connect=10.0)

def get_popular_movies(page=1):
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(
            f"{BASE_URL}/movie/popular",
            params={
                "api_key": settings.TMDB_API_KEY,
                "language": "en-US",
                "page": page,
            }
        )
        response.raise_for_status()
        return response.json()


def get_genres_map():
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(
            f"{BASE_URL}/genre/movie/list",
            params={
                "api_key": settings.TMDB_API_KEY,
                "language": "en-US",
            }
        )
        response.raise_for_status()

        return {
            genre["id"]: genre["name"]
            for genre in response.json().get("genres", [])
        }

def get_movie_genres(tmdb_id):
    url = f"{BASE_URL}/movie/{tmdb_id}"
    params = {
        "api_key": settings.TMDB_API_KEY,
        "language": "en-US",
    }

    with httpx.Client(timeout=15) as client:
        response = client.get(url, params=params)
        response.raise_for_status()

    return [g["id"] for g in response.json().get("genres", [])]

def get_tmdb_genres():
    import requests
    from django.conf import settings

    url = "https://api.themoviedb.org/3/genre/movie/list"
    params = {
        "api_key": settings.TMDB_API_KEY,
        "language": "en-US"
    }

    res = requests.get(url, params=params)
    res.raise_for_status()
    return res.json().get("genres", [])

