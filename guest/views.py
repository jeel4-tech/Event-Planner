from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from user.models import Event, EventGuestAccess, GuestNotification, GuestNotificationPreference
from vendor.models import Booking, GalleryImage, GuestSelfie, Chat, ChatMessage


def guest_dashboard(request):
    """Guest dashboard showing event information"""
    access_id = request.session.get('guest_access_id')
    
    if not access_id:
        messages.error(request, 'Please login to access the event')
        return redirect('login')
    
    try:
        access = EventGuestAccess.objects.select_related('event', 'event__owner').get(id=access_id, is_active=True)
        event = access.event
        
        # Get bookings for this event
        bookings = Booking.objects.filter(event=event).select_related('store', 'service', 'vendor', 'customer')
        
        # Get gallery images for this event
        gallery_images = GalleryImage.objects.filter(event=event).order_by('-uploaded_at')
        
        return render(request, 'guest/dashboard.html', {
            'event': event,
            'access': access,
            'bookings': bookings,
            'gallery_images': gallery_images,
        })
    except EventGuestAccess.DoesNotExist:
        messages.error(request, 'Your access has been revoked or expired')
        request.session.flush()
        return redirect('login')


def guest_logout(request):
    """Logout guest"""
    request.session.flush()
    messages.success(request, 'You have been logged out')
    return redirect('login')


def _get_guest_access(request):
    """Helper to get current guest access or None."""
    access_id = request.session.get('guest_access_id')
    if not access_id:
        return None
    try:
        return EventGuestAccess.objects.select_related('event').get(id=access_id, is_active=True)
    except EventGuestAccess.DoesNotExist:
        return None


def guest_notifications(request):
    """Guest notification center."""
    access = _get_guest_access(request)
    if not access:
        messages.error(request, 'Please login to view notifications.')
        return redirect('login')

    notifications = GuestNotification.objects.filter(guest_access=access).order_by('-created_at')[:50]
    GuestNotification.objects.filter(guest_access=access, is_read=False).update(is_read=True)
    gallery_images = GalleryImage.objects.filter(event=access.event).order_by('-uploaded_at')

    return render(request, 'guest/notifications.html', {
        'event': access.event,
        'access': access,
        'gallery_images': gallery_images,
        'notifications': notifications,
    })


def guest_notification_preferences(request):
    """Guest notification preferences."""
    access = _get_guest_access(request)
    if not access:
        messages.error(request, 'Please login to manage preferences.')
        return redirect('login')

    pref, _ = GuestNotificationPreference.objects.get_or_create(
        guest_access=access,
        defaults={'notify_new_photos': True, 'notify_event_updates': True},
    )

    if request.method == 'POST':
        pref.notify_new_photos = request.POST.get('notify_new_photos') == 'on'
        pref.notify_event_updates = request.POST.get('notify_event_updates') == 'on'
        pref.save()
        # Update display name for chat (shown to photographer)
        guest_name = (request.POST.get('guest_name') or '').strip()
        access.guest_name = guest_name[:120] if guest_name else ''
        access.save(update_fields=['guest_name'])
        messages.success(request, 'Preferences updated.')
        return redirect('guest_notification_preferences')

    gallery_images = GalleryImage.objects.filter(event=access.event).order_by('-uploaded_at')

    return render(request, 'guest/notification_preferences.html', {
        'event': access.event,
        'access': access,
        'gallery_images': gallery_images,
        'pref': pref,
    })


def guest_face_search(request):
    """
    Guest uploads a selfie; DeepFace extracts its ArcFace embedding and
    compares it against all photographer-uploaded GalleryImages for the event.
    """
    access_id = request.session.get('guest_access_id')
    if not access_id:
        messages.error(request, 'Please login to use this feature.')
        return redirect('login')

    try:
        access = EventGuestAccess.objects.select_related('event').get(id=access_id, is_active=True)
    except EventGuestAccess.DoesNotExist:
        messages.error(request, 'Your access has been revoked or expired.')
        request.session.flush()
        return redirect('login')

    event = access.event
    matched_photos = None
    selfie_url = None
    search_done = False
    error_msg = None

    if request.method == 'POST':
        selfie_file = request.FILES.get('selfie')
        if not selfie_file:
            messages.error(request, 'Please upload a selfie image.')
            return redirect('guest_face_search')

        selfie_obj = GuestSelfie.objects.create(
            event=event,
            guest_access=access,
            image=selfie_file,
        )
        selfie_url = selfie_obj.image.url

        try:
            from vendor.deepface_utils import (
                extract_single_embedding,
                find_matching_gallery_images,
            )

            selfie_embedding = extract_single_embedding(selfie_obj.image.path)

            if selfie_embedding is None:
                error_msg = 'No face detected in your selfie. Please upload a clear, front-facing photo.'
            else:
                from vendor.deepface_utils import _safe_tolist
                selfie_obj.face_embedding = _safe_tolist(selfie_embedding)
                selfie_obj.save(update_fields=['face_embedding'])

                gallery_qs = GalleryImage.objects.filter(
                    event=event,
                    uploaded_by_guest=False,
                )
                # Returns list of (distance, GalleryImage) tuples
                raw_matches = find_matching_gallery_images(selfie_embedding, gallery_qs)
                matched_photos = [
                    {'photo': img, 'distance': round(dist, 4), 'score': round((1 - dist) * 100, 1)}
                    for dist, img in raw_matches
                ]

                search_done = True

        except ImportError:
            error_msg = 'Face recognition service is temporarily unavailable. Please try again later.'
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Face search error: %s", exc, exc_info=True)
            error_msg = f'An error occurred during face recognition: {exc}'

    total_photos = GalleryImage.objects.filter(event=event, uploaded_by_guest=False).count()
    indexed_photos = GalleryImage.objects.filter(
        event=event, uploaded_by_guest=False, embedding_status='done'
    ).count()
    gallery_images = GalleryImage.objects.filter(event=event).order_by('-uploaded_at')

    return render(request, 'guest/face_search.html', {
        'event': event,
        'access': access,
        'gallery_images': gallery_images,
        'matched_photos': matched_photos,
        'selfie_url': selfie_url,
        'search_done': search_done,
        'error_msg': error_msg,
        'total_photos': total_photos,
        'indexed_photos': indexed_photos,
    })


def guest_chat(request):
    """List chat conversations with vendors (one per event)."""
    access = _get_guest_access(request)
    if not access:
        messages.error(request, 'Please login to access chat.')
        return redirect('login')

    chats = Chat.objects.filter(guest_access=access).select_related('vendor', 'store').annotate(
        unread_count=Count('messages', filter=Q(messages__is_read=False))
    )

    return render(request, 'guest/chat.html', {
        'event': access.event,
        'access': access,
        'chats': chats,
        'gallery_images': GalleryImage.objects.filter(event=access.event).order_by('-uploaded_at'),
    })


def guest_chat_detail(request, chat_id):
    """Chat thread with a vendor."""
    access = _get_guest_access(request)
    if not access:
        messages.error(request, 'Please login to access chat.')
        return redirect('login')

    chat = get_object_or_404(Chat, id=chat_id, guest_access=access)

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        image = request.FILES.get('image')
        if message_text or image:
            ChatMessage.objects.create(
                chat=chat,
                guest_sender=access,
                message=message_text or '',
                image=image,
                is_read=True,  # Own message, no unread badge for guest
            )
        return redirect('guest_chat_detail', chat_id=chat.id)

    # Mark vendor's messages as read
    chat.messages.filter(is_read=False).filter(sender_id=chat.vendor_id).update(is_read=True)

    messages_qs = chat.messages.select_related('sender', 'guest_sender', 'guest_sender__event').all()

    return render(request, 'guest/chat_detail.html', {
        'event': access.event,
        'access': access,
        'chat': chat,
        'messages': messages_qs,
        'gallery_images': GalleryImage.objects.filter(event=access.event).order_by('-uploaded_at'),
    })


def guest_start_chat(request):
    """Create or open chat with the event's vendor."""
    access = _get_guest_access(request)
    if not access:
        messages.error(request, 'Please login to start a chat.')
        return redirect('login')

    chat, _ = Chat.objects.get_or_create(
        guest_access=access,
        vendor=access.vendor,
        defaults={'store': None}
    )
    return redirect('guest_chat_detail', chat_id=chat.id)