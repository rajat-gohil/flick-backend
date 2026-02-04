import json
from channels.generic.websocket import AsyncWebsocketConsumer


class MatchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.group_name = f"session_{self.session_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Notify other participant that someone disconnected
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "partner_disconnected",
                "channel": self.channel_name,
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
