from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Message

@receiver(post_save, sender=Message)
def broadcast_new_message(sender, instance, created, **kwargs):
    if created:
        channel_layer = get_channel_layer()
        if channel_layer:
            # Determine room name
            user_ids = sorted([instance.sender.id, instance.receiver.id])
            room_group_name = f"chat_{user_ids[0]}_{user_ids[1]}"
            
            # Format message data
            message_data = {
                'id': instance.id,
                'sender_id': instance.sender.id,
                'content': instance.content,
                'timestamp': instance.timestamp.strftime('%I:%M %p'), # e.g., 05:30 PM
                'attachment_url': instance.attachment.url if instance.attachment else None,
                'is_image': False
            }
            
            if instance.attachment:
                ext = str(instance.attachment.name).lower().split('.')[-1]
                if ext in ['jpg', 'jpeg', 'png', 'gif']:
                    message_data['is_image'] = True

            # Send to room group
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'chat_message',
                    'message_data': message_data
                }
            )
