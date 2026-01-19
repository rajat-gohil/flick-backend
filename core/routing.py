from django.urls import path
from .consumers import MatchConsumer

websocket_urlpatterns = [
    path("ws/session/<int:session_id>/", MatchConsumer.as_asgi()),
]
