from django.contrib import admin
from .models import MuteList, Message, PublicPost, Comment, Notification

@admin.register(MuteList)
class MuteListAdmin(admin.ModelAdmin):
    list_display = ('muter', 'muted_user', 'created_at')
    search_fields = ('muter__username', 'muted_user__username')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'is_read', 'timestamp')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('sender__username', 'receiver__username', 'content')

@admin.register(PublicPost)
class PublicPostAdmin(admin.ModelAdmin):
    list_display = ('author', 'status', 'created_at', 'total_likes')
    list_filter = ('status', 'created_at')
    search_fields = ('author__username', 'caption')
    actions = ['approve_posts', 'reject_posts']

    def approve_posts(self, request, queryset):
        queryset.update(status='APPROVED')
    approve_posts.short_description = "Mark selected posts as Approved"

    def reject_posts(self, request, queryset):
        queryset.update(status='REJECTED')
    reject_posts.short_description = "Mark selected posts as Rejected"

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'created_at')
    search_fields = ('author__username', 'content')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'title')
