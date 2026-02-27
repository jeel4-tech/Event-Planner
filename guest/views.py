from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from user.models import Event, EventGuestAccess
from vendor.models import Booking, GalleryImage

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