from django.urls import path
from . import views

urlpatterns = [
    # Feed & Posts
    path('feed/', views.feed_view, name='campus_feed'),
    path('feed/create/', views.create_post, name='create_post'),
    path('feed/like/<int:post_id>/', views.like_post, name='like_post'),
    path('feed/comment/<int:post_id>/', views.add_comment, name='add_comment'),
    
    # Messaging
    path('chat/', views.chat_hub, name='chat_hub'),
    path('chat/<int:user_id>/', views.chat_room, name='chat_room'),
    path('chat/mute/<int:user_id>/', views.toggle_mute, name='toggle_mute'),
    
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    
    # Profile
    path('profile/', views.profile_view, name='profile_view'),
    
    # Moderation
    path('moderation/', views.moderation_queue, name='moderation_queue'),
    path('moderation/approve/<int:post_id>/', views.approve_post, name='approve_post'),
    path('moderation/reject/<int:post_id>/', views.reject_post, name='reject_post'),

    # Reporting
    path('report/submit/', views.submit_report, name='submit_report'),
    path('moderation/reports/', views.view_reports, name='view_reports'),
    path('moderation/reports/resolve/<int:report_id>/', views.resolve_report, name='resolve_report'),
]