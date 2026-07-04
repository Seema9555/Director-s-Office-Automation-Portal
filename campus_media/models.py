from django.db import models
from django.contrib.auth.models import User

# ==========================================
# 1. MESSAGING & PRIVACY MODELS
# ==========================================

class MuteList(models.Model):
    """
    Allows a user (muter) to block/mute messages from another user (muted_user).
    """
    muter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="muted_users")
    muted_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="muted_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('muter', 'muted_user')
        verbose_name_plural = "Mute Lists"

    def __str__(self):
        return f"{self.muter.username} muted {self.muted_user.username}"


class Message(models.Model):
    """
    Direct 1-on-1 messaging between any two users.
    """
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='campus_media/messages/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"From {self.sender.username} to {self.receiver.username} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"


# ==========================================
# 2. PUBLIC FEED MODELS
# ==========================================

class PublicPost(models.Model):
    """
    Instagram-style public posts. 
    Requires Director approval unless the Director is the author.
    """
    STATUS_CHOICES = (
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='public_posts')
    image = models.ImageField(upload_to='campus_media/posts/images/', blank=True, null=True)
    video = models.FileField(upload_to='campus_media/posts/videos/', blank=True, null=True)
    caption = models.TextField(blank=True, max_length=1000)
    is_announcement = models.BooleanField(default=False, help_text="Pinned announcement with comments disabled.")
    
    # Moderation
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    admin_remark = models.TextField(blank=True, help_text="Reason for rejection, if any.")
    
    # Interactions
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Post by {self.author.username} - {self.status}"

    @property
    def total_likes(self):
        return self.likes.count()


class Comment(models.Model):
    """
    Comments on Public Posts.
    """
    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_comments')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Oldest first like Instagram

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.id}"


# ==========================================
# 3. NOTIFICATION MODEL
# ==========================================

class Notification(models.Model):
    """
    Alerts for users (e.g. Post Approved, New Message, Post Rejected)
    """
    TYPE_CHOICES = (
        ('POST_APPROVED', 'Post Approved'),
        ('POST_REJECTED', 'Post Rejected'),
        ('NEW_MESSAGE', 'New Message'),
        ('NEW_LIKE', 'New Like'),
        ('NEW_COMMENT', 'New Comment'),
    )

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=100)
    message = models.CharField(max_length=255)
    
    # Optional link to navigate to the specific post or chat
    link = models.CharField(max_length=255, blank=True)
    
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"To {self.recipient.username}: {self.title}"

# ==========================================
# 6. REPORT MODEL
# ==========================================

class Report(models.Model):
    """
    Model for storing user reports containing automatic screenshots.
    """
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_filed')
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received', null=True, blank=True)
    post = models.ForeignKey(PublicPost, on_delete=models.CASCADE, null=True, blank=True)
    reason = models.TextField()
    screenshot = models.ImageField(upload_to='campus_media/reports/screenshots/')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter.username}"