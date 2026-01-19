from django.contrib import admin
from .models import Session, Movie, Swipe, Match

admin.site.register(Session)
admin.site.register(Movie)
admin.site.register(Swipe)
admin.site.register(Match)
