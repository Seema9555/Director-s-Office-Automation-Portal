import json
from channels.generic.websocket import AsyncWebsocketConsumer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Security: Only allow authenticated users
        if not self.user.is_authenticated:
            await self.close()
            return
            
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        
        # Create a unique room name based on the two user IDs
        # Sorting ensures both users connect to the same room regardless of who initiated
        user_ids = sorted([self.user.id, int(self.other_user_id)])
        self.room_group_name = f"chat_{user_ids[0]}_{user_ids[1]}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket (Frontend to Server)
    # We are using HTTP POST for sending messages to handle files and moderation easily,
    # so we don't strictly need to handle incoming WS messages here unless desired.
    async def receive(self, text_data):
        pass

    # Receive message from room group (Server to Frontend)
    async def chat_message(self, event):
        message_data = event['message_data']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message_data': message_data
        }))
