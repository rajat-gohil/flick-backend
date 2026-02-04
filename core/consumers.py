import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser



class MatchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"session_{self.session_id}"
        self.user = self.scope.get("user")

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        if self.user and not isinstance(self.user, AnonymousUser):
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "presence_event",
                    "user_id": self.user.id,
                    "status": "online",
                }
            )

    async def disconnect(self, close_code):
        if self.user and not isinstance(self.user, AnonymousUser):
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "presence_event",
                    "user_id": self.user.id,
                    "status": "offline",
                }
            )

        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )


    async def match_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "match_event",
            "session_id": event["session_id"],
            "movie_id": event["movie_id"],
            "movie_title": event["movie_title"],
        }))


    async def session_ended_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "session_ended",
            "session_id": event["session_id"],
        }))


    async def swipe_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "partner_swiping",
            "user_id": event["user_id"],
        }))

    async def partner_disconnected(self, event):
    # Do not notify the user who disconnected
        if self.channel_name == event.get("channel"):
            return

        await self.send(text_data=json.dumps({
            "type": "partner_disconnected",
        }))

    async def presence_event(self, event):
        await self.send(text_data=json.dumps({
            "type": "presence",
            "user_id": event["user_id"],
            "status": event["status"],
        }))