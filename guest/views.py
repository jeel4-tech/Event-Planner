from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from user.models import Event, EventGuestAccess
from vendor.models import Booking, GalleryImage, GuestSelfie


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

    return render(request, 'guest/face_search.html', {
        'event': event,
        'access': access,
        'matched_photos': matched_photos,
        'selfie_url': selfie_url,
        'search_done': search_done,
        'error_msg': error_msg,
        'total_photos': total_photos,
        'indexed_photos': indexed_photos,
    })