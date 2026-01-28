#!/usr/bin/env bash

echo "Running migrations..."
python manage.py migrate --noinput

echo "Syncing genres from TMDB..."
python manage.py sync_genres || true

echo "Syncing movies from TMDB..."
python manage.py sync_movies || true

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting server..."
gunicorn backend.wsgi:application
