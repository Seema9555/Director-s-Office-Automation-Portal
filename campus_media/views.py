from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from .models import PublicPost, Message, MuteList, Comment, Notification, Report
from .utils import censor_text
from django.http import JsonResponse
import base64
import uuid
from django.core.files.base import ContentFile

# ==========================================
# 1. PUBLIC FEED VIEWS
# ==========================================

@login_required
def feed_view(request):
    """
    Displays the main social feed with approved posts.
    """
    posts = PublicPost.objects.filter(status='APPROVED').prefetch_related('comments', 'likes').order_by('-is_announcement', '-created_at')
    
    # Check if the user is a director or teacher
    is_director = request.user.is_superuser
    is_teacher = hasattr(request.user, 'teacher_profile')
    is_authorized_announcer = is_director or is_teacher
    
    context = {
        'posts': posts,
        'is_director': is_director,
        'is_authorized_announcer': is_authorized_announcer,
    }
    return render(request, 'campus_media/feed.html', context)

@login_required
def create_post(request):
    """
    Handles the submission of a new post.
    """
    if request.method == 'POST':
        caption = request.POST.get('caption', '')
        image = request.FILES.get('image')
        video = request.FILES.get('video')
        
        is_announcement_flag = request.POST.get('is_announcement') == 'on'
        is_authorized_announcer = request.user.is_superuser or hasattr(request.user, 'teacher_profile')
        is_announcement = is_announcement_flag if is_authorized_announcer else False
        
        # Director's posts are automatically approved.
        # Students and Teachers need approval.
        status = 'APPROVED' if request.user.is_superuser else 'PENDING'
        
        post = PublicPost.objects.create(
            author=request.user,
            caption=caption,
            image=image,
            video=video,
            status=status,
            is_announcement=is_announcement
        )
        
        if status == 'PENDING':
            messages.success(request, "Your post has been submitted and is pending Director approval.")
        else:
            messages.success(request, "Post published successfully.")
            
    return redirect('campus_feed')

@login_required
def like_post(request, post_id):
    """
    Toggles a like on a post.
    """
    if request.method == 'POST':
        post = get_object_or_404(PublicPost, id=post_id, status='APPROVED')
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True
            
            # Send notification to post author
            if request.user != post.author:
                Notification.objects.create(
                    recipient=post.author,
                    notification_type='NEW_LIKE',
                    title='New Like',
                    message=f'{request.user.first_name or request.user.username} liked your post.',
                    link=f'/social/feed/#post-{post.id}'
                )
                
        return JsonResponse({'liked': liked, 'total_likes': post.total_likes})
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def add_comment(request, post_id):
    """
    Adds a comment to a post.
    """
    if request.method == 'POST':
        post = get_object_or_404(PublicPost, id=post_id, status='APPROVED')
        content = request.POST.get('content')
        if content:
            censored_content = censor_text(content)
            Comment.objects.create(
                post=post,
                author=request.user,
                content=censored_content
            )
            
            # Send notification to post author
            if request.user != post.author:
                Notification.objects.create(
                    recipient=post.author,
                    notification_type='NEW_COMMENT',
                    title='New Comment',
                    message=f'{request.user.first_name or request.user.username} commented on your post.',
                    link=f'/social/feed/#post-{post.id}'
                )
            messages.success(request, "Comment added.")
    return redirect('campus_feed')

# ==========================================
# 2. MESSAGING VIEWS
# ==========================================

@login_required
def chat_hub(request):
    """
    Displays the user's active conversations or allows searching for new users.
    """
    # Fetch all users except the current user to display in a directory/search
    users = User.objects.exclude(id=request.user.id)
    
    # Logic to get latest conversations
    recent_messages = Message.objects.filter(
        Q(sender=request.user) | Q(receiver=request.user)
    ).select_related('sender', 'receiver').order_by('-timestamp')
    
    recent_users = []
    seen_users = set()
    for msg in recent_messages:
        other_user = msg.sender if msg.receiver == request.user else msg.receiver
        if other_user.id not in seen_users:
            seen_users.add(other_user.id)
            other_user.latest_message = msg
            recent_users.append(other_user)
            
    context = {
        'users': users,
        'recent_users': recent_users,
    }
    return render(request, 'campus_media/chat_hub.html', context)

@login_required
def chat_room(request, user_id):
    """
    Displays the direct messaging thread with a specific user.
    """
    other_user = get_object_or_404(User, id=user_id)
    
    # Check if the current user is muted by the other user
    is_muted_by_them = MuteList.objects.filter(muter=other_user, muted_user=request.user).exists()
    
    # Check if the current user has muted the other user
    has_muted_them = MuteList.objects.filter(muter=request.user, muted_user=other_user).exists()

    # Get messages
    messages_list = Message.objects.filter(
        (Q(sender=request.user) & Q(receiver=other_user)) | 
        (Q(sender=other_user) & Q(receiver=request.user))
    ).order_by('timestamp')
    
    # Mark messages as read
    Message.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    # Calculate daily tokens
    today = timezone.now().date()
    messages_today_count = Message.objects.filter(sender=request.user, timestamp__date=today).count()
    daily_limit = 20
    tokens_remaining = max(0, daily_limit - messages_today_count)

    if request.method == 'POST' and not is_muted_by_them:
        if tokens_remaining <= 0:
            messages.error(request, "Daily message limit reached. You can only send 20 messages per day.")
            return redirect('chat_room', user_id=other_user.id)

        content = request.POST.get('content', '')
        attachment = request.FILES.get('attachment')
        
        if content or attachment:
            censored_content = censor_text(content)
            Message.objects.create(
                sender=request.user,
                receiver=other_user,
                content=censored_content,
                attachment=attachment
            )
            
            # Create Notification
            Notification.objects.create(
                recipient=other_user,
                notification_type='NEW_MESSAGE',
                title='New Message',
                message=f'You received a new message from {request.user.first_name or request.user.username}',
                link=f'/social/chat/{request.user.id}/'
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'ok'})
                
            return redirect('chat_room', user_id=other_user.id)

    context = {
        'other_user': other_user,
        'messages_list': messages_list,
        'is_muted_by_them': is_muted_by_them,
        'has_muted_them': has_muted_them,
        'tokens_remaining': tokens_remaining,
        'daily_limit': daily_limit,
    }
    return render(request, 'campus_media/chat_room.html', context)

@login_required
def toggle_mute(request, user_id):
    """
    Mutes or unmutes a user.
    """
    other_user = get_object_or_404(User, id=user_id)
    mute_record = MuteList.objects.filter(muter=request.user, muted_user=other_user).first()
    
    if mute_record:
        mute_record.delete()
        messages.success(request, f"You have unmuted {other_user.username}.")
    else:
        MuteList.objects.create(muter=request.user, muted_user=other_user)
        messages.success(request, f"You have muted {other_user.username}. They can no longer message you.")
        
    return redirect('chat_room', user_id=user_id)

# ==========================================
# 3. NOTIFICATIONS VIEW
# ==========================================

@login_required
def notifications_view(request):
    """
    Displays the user's notifications.
    """
    notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Mark all as read upon viewing
    notifs.update(is_read=True)
    
    context = {
        'notifications': notifs,
    }
    return render(request, 'campus_media/notifications.html', context)

# ==========================================
# 4. PROFILE VIEW
# ==========================================

@login_required
def profile_view(request):
    """
    Displays the user's profile with information from the main portal.
    """
    user = request.user
    role = "Director" if user.is_superuser else "Unknown"
    profile_data = None

    if hasattr(user, 'student_profile'):
        role = "Student"
        profile_data = user.student_profile
    elif hasattr(user, 'teacher_profile'):
        role = "Teacher"
        profile_data = user.teacher_profile

    # Fetch user's own posts
    user_posts = PublicPost.objects.filter(author=user).order_by('-created_at')

    context = {
        'role': role,
        'profile_data': profile_data,
        'user_posts': user_posts,
    }
    return render(request, 'campus_media/profile.html', context)

# ==========================================
# 5. MODERATION VIEWS
# ==========================================

@login_required
def moderation_queue(request):
    """
    Displays pending posts for the Director to review.
    """
    if not request.user.is_superuser:
        return redirect('campus_feed')
    pending_posts = PublicPost.objects.filter(status='PENDING').order_by('-created_at')
    return render(request, 'campus_media/moderation.html', {'pending_posts': pending_posts})

@login_required
def approve_post(request, post_id):
    if request.user.is_superuser:
        post = get_object_or_404(PublicPost, id=post_id)
        post.status = 'APPROVED'
        post.save()
        
        Notification.objects.create(
            recipient=post.author,
            notification_type='POST_APPROVED',
            title='Post Approved',
            message='Your recent post has been approved and is now visible on the feed.',
            link=f'/social/feed/#post-{post.id}'
        )
        messages.success(request, "Post approved.")
    return redirect('moderation_queue')

@login_required
def reject_post(request, post_id):
    if request.user.is_superuser:
        post = get_object_or_404(PublicPost, id=post_id)
        post.status = 'REJECTED'
        post.admin_remark = "Does not comply with campus guidelines."
        post.save()
        
        Notification.objects.create(
            recipient=post.author,
            notification_type='POST_REJECTED',
            title='Post Rejected',
            message='Your recent post was rejected by the Director.',
        )
        messages.success(request, "Post rejected.")
    return redirect('moderation_queue')

# ==========================================
# 6. REPORTING VIEWS
# ==========================================

@login_required
def submit_report(request):
    """
    AJAX endpoint to submit a report with an auto-generated screenshot.
    """
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        reported_id = request.POST.get('reported_id')
        reason = request.POST.get('reason', '')
        screenshot_data = request.POST.get('screenshot')

        if not screenshot_data:
            return JsonResponse({'error': 'Screenshot missing'}, status=400)

        # Decode base64 screenshot
        try:
            format, imgstr = screenshot_data.split(';base64,') 
            ext = format.split('/')[-1]
            if ext not in ['jpeg', 'png', 'webp']:
                return JsonResponse({'error': 'Invalid image format'}, status=400)
                
            image_name = f"report_{uuid.uuid4().hex}.{ext}"
            data = ContentFile(base64.b64decode(imgstr), name=image_name)
        except Exception as e:
            return JsonResponse({'error': 'Failed to process screenshot'}, status=400)

        report = Report(reporter=request.user, reason=reason, screenshot=data)

        if report_type == 'post':
            post = get_object_or_404(PublicPost, id=reported_id)
            report.post = post
            report_title = f"New Post Report by {request.user.username}"
            report_msg = f"Post #{post.id} was reported."
        elif report_type == 'user':
            user = get_object_or_404(User, id=reported_id)
            report.reported_user = user
            report_title = f"New User Report by {request.user.username}"
            report_msg = f"User {user.username} was reported."
        else:
            return JsonResponse({'error': 'Invalid report type'}, status=400)

        report.save()

        # Notify directors
        directors = User.objects.filter(is_superuser=True)
        for director in directors:
            Notification.objects.create(
                recipient=director,
                notification_type='NEW_MESSAGE',
                title=report_title,
                message=report_msg,
                link='/social/moderation/reports/'
            )

        return JsonResponse({'status': 'ok', 'message': 'Report submitted successfully. The Director has been notified.'})
        
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def view_reports(request):
    """
    Displays pending reports for the Director.
    """
    if not request.user.is_superuser:
        return redirect('campus_feed')
    
    pending_reports = Report.objects.filter(is_resolved=False).order_by('-created_at')
    return render(request, 'campus_media/reports.html', {'pending_reports': pending_reports})

@login_required
def resolve_report(request, report_id):
    if request.user.is_superuser:
        report = get_object_or_404(Report, id=report_id)
        report.is_resolved = True
        report.save()
        messages.success(request, "Report marked as resolved.")
    return redirect('view_reports')



@login_required
def create_post(request):
    """
    Handles the submission of a new post and renders the creation page.
    """
    if request.method == 'POST':
        caption = request.POST.get('content', '') # Frontend mein textarea ka name 'content' hai
        image = request.FILES.get('media') # Frontend mein file input ka name 'media' hai
        video = request.FILES.get('media') # Agar video hai toh bhi isi se aayega
        
        # Determine if it's an image or video based on content type
        final_image = image if image and image.content_type.startswith('image/') else None
        final_video = video if video and video.content_type.startswith('video/') else None

        is_announcement_flag = request.POST.get('is_announcement') == 'true'
        is_authorized_announcer = request.user.is_superuser or hasattr(request.user, 'teacher_profile')
        is_announcement = is_announcement_flag if is_authorized_announcer else False
        
        # Director's posts are automatically approved.
        # Students and Teachers need approval.
        status = 'APPROVED' if request.user.is_superuser else 'PENDING'
        
        post = PublicPost.objects.create(
            author=request.user,
            caption=caption,
            image=final_image,
            video=final_video,
            status=status,
            is_announcement=is_announcement
        )
        
        if status == 'PENDING':
            messages.success(request, "Your post has been submitted and is pending Director approval.")
        else:
            messages.success(request, "Post published successfully.")
            
        return redirect('campus_feed')

    # Niche wali line miss thi tumhare code mein! Yehi page load karegi.
    return render(request, 'campus_media/create_post.html')