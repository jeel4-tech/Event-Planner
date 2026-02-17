from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from account.models import User
from user.models import Event, Payment, Review, Notification
from vendor.models import (
    Store, category as Category, Service, Booking, VendorEarning, StoreImage,
    Chat, ChatMessage
)
from decimal import Decimal

def vendor_required(view_func):
    """Decorator to check if user is a vendor"""
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if not user_id or role != 'vendor':
            return redirect('login')
        
        try:
            vendor = User.objects.get(id=user_id)
        except User.DoesNotExist:
            request.session.flush()
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@vendor_required
def vendor_dashboard(request):
    vendor_id = request.session.get('user_id')
    vendor = User.objects.get(id=vendor_id)
    
    # Get vendor's stores
    stores = Store.objects.filter(vendor_id=vendor_id)
    store_ids = stores.values_list('id', flat=True)
    
    # Calculate statistics
    total_stores = stores.count()
    total_services = Service.objects.filter(store__vendor_id=vendor_id).count()
    total_bookings = Booking.objects.filter(vendor_id=vendor_id).count()
    pending_bookings = Booking.objects.filter(vendor_id=vendor_id, status=Booking.STATUS_PENDING).count()
    confirmed_bookings = Booking.objects.filter(vendor_id=vendor_id, status=Booking.STATUS_CONFIRMED).count()
    
    # Earnings
    total_earnings = VendorEarning.objects.filter(
        vendor_id=vendor_id,
        payment_status=Payment.STATUS_SUCCESS
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
    
    pending_earnings = VendorEarning.objects.filter(
        vendor_id=vendor_id,
        payment_status=Payment.STATUS_PENDING
    ).aggregate(total=Sum('net_amount'))['total'] or Decimal('0.00')
    
    # Recent bookings
    recent_bookings = Booking.objects.filter(vendor_id=vendor_id).order_by('-created_at')[:5]
    
    # Upcoming events (from bookings)
    upcoming_bookings = Booking.objects.filter(
        vendor_id=vendor_id,
        status__in=[Booking.STATUS_CONFIRMED, Booking.STATUS_IN_PROGRESS],
        booking_date__gte=timezone.now()
    ).order_by('booking_date')[:5]
    
    # Recent reviews
    recent_reviews = Review.objects.filter(
        event__bookings__vendor_id=vendor_id
    ).distinct().order_by('-created_at')[:5]
    
    return render(request, 'vendor/dashboard.html', {
        'vendor': vendor,
        'total_stores': total_stores,
        'total_services': total_services,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'total_earnings': total_earnings,
        'pending_earnings': pending_earnings,
        'recent_bookings': recent_bookings,
        'upcoming_bookings': upcoming_bookings,
        'recent_reviews': recent_reviews,
    })


@vendor_required
def vendor_store(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    stores = Store.objects.filter(vendor_id=vendor_id)
    categories = Category.objects.all()

    edit_id = request.GET.get('edit')
    editing_store = None
    if edit_id:
        try:
            editing_store = stores.get(id=edit_id)
        except Store.DoesNotExist:
            editing_store = None

    if request.method == "POST":
        store_name = request.POST.get("store_name")
        description = request.POST.get("description")
        category_id = request.POST.get("category")
        address = request.POST.get("address")
        city = request.POST.get("city")
        price_start = request.POST.get("price_start")
        phone = request.POST.get("phone")
        image = request.FILES.get("profile_image")

        selected_category = None
        if category_id:
            try:
                selected_category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                selected_category = None

        store_id = request.POST.get('store_id')

        if store_id:
            try:
                store = stores.get(id=store_id)
                store.store_name = store_name
                store.description = description
                if selected_category:
                    store.category = selected_category
                store.phone = phone
                store.address = address
                store.city = city
                store.price_start = price_start
                if image:
                    store.profile_image = image
                store.save()
                # handle multiple store images
                files = request.FILES.getlist('store_images')
                for f in files:
                    StoreImage.objects.create(store=store, image=f)
                messages.success(request, 'Store updated successfully!')
            except Store.DoesNotExist:
                messages.error(request, 'Store not found!')
        else:
            store = Store.objects.create(
                vendor_id=vendor_id,
                store_name=store_name,
                description=description,
                category=selected_category,
                phone=phone,
                address=address,
                city=city,
                price_start=price_start,
                profile_image=image
            )
            # handle multiple store images
            files = request.FILES.getlist('store_images')
            for f in files:
                StoreImage.objects.create(store=store, image=f)
            messages.success(request, 'Store created successfully!')

        return redirect("vendor_store")

    return render(request, "vendor/mystore.html", {
        "stores": stores,
        "categories": categories,
        "editing_store": editing_store,
        "vendor": vendor
    })


@vendor_required
def vendor_services(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    stores = Store.objects.filter(vendor_id=vendor_id)
    services = Service.objects.filter(store__vendor_id=vendor_id).select_related('store')
    
    if request.method == "POST":
        service_id = request.POST.get('service_id')
        store_id = request.POST.get('store')
        name = request.POST.get('name')
        description = request.POST.get('description')
        price = request.POST.get('price')
        duration = request.POST.get('duration')
        image = request.FILES.get('image')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            store = stores.get(id=store_id)
        except Store.DoesNotExist:
            messages.error(request, 'Invalid store selected!')
            return redirect('vendor_services')
        
        if service_id:
            try:
                service = services.get(id=service_id)
                service.store = store
                service.name = name
                service.description = description
                service.price = price
                service.duration = duration
                service.is_active = is_active
                if image:
                    service.image = image
                service.save()
                messages.success(request, 'Service updated successfully!')
            except Service.DoesNotExist:
                messages.error(request, 'Service not found!')
        else:
            Service.objects.create(
                store=store,
                name=name,
                description=description,
                price=price,
                duration=duration,
                image=image,
                is_active=is_active
            )
            messages.success(request, 'Service created successfully!')
        
        return redirect('vendor_services')
    
    return render(request, 'vendor/services.html', {
        'services': services,
        'stores': stores,
        'vendor': vendor,
    })


@vendor_required
def delete_service(request, service_id):
    vendor_id = request.session.get("user_id")
    try:
        service = Service.objects.get(id=service_id, store__vendor_id=vendor_id)
        service.delete()
        messages.success(request, 'Service deleted successfully!')
    except Service.DoesNotExist:
        messages.error(request, 'Service not found!')
    return redirect('vendor_services')


@vendor_required
def vendor_orders(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    bookings = Booking.objects.filter(vendor_id=vendor_id).select_related(
        'event', 'store', 'service', 'customer'
    ).order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)
    
    if request.method == "POST":
        booking_id = request.POST.get('booking_id')
        action = request.POST.get('action')
        
        try:
            booking = bookings.get(id=booking_id)
            
            if action == 'confirm':
                booking.status = Booking.STATUS_CONFIRMED
                booking.save()
                Notification.objects.create(
                    user=booking.customer,
                    title='Booking Approved',
                    message=f'Your booking for {booking.store.store_name} has been approved.',
                    is_read=False
                )
                messages.success(request, 'Booking confirmed!')
            elif action == 'cancel':
                booking.status = Booking.STATUS_CANCELLED
                booking.save()
                try:
                    Notification.objects.create(
                        user=booking.customer,
                        title='Booking Rejected',
                        message=f'Your booking for {booking.store.store_name} was cancelled by the vendor.',
                        is_read=False
                    )
                except Exception:
                    pass
                messages.success(request, 'Booking cancelled!')
            elif action == 'complete':
                booking.status = Booking.STATUS_COMPLETED
                booking.save()
                # Create earning record if not exists
                if not hasattr(booking, 'earning'):
                    commission_rate = Decimal('10.00')  # 10% platform commission
                    commission_amount = booking.amount * commission_rate / 100
                    net_amount = booking.amount - commission_amount
                    VendorEarning.objects.create(
                        vendor_id=vendor_id,
                        booking=booking,
                        amount=booking.amount,
                        commission_rate=commission_rate,
                        net_amount=net_amount,
                        payment_status=Payment.STATUS_PENDING
                    )
                messages.success(request, 'Booking marked as completed!')
        except Booking.DoesNotExist:
            messages.error(request, 'Booking not found!')
        
        return redirect('vendor_orders')
    
    return render(request, 'vendor/orders.html', {
        'bookings': bookings,
        'status_filter': status_filter,
        'vendor': vendor,
    })


@vendor_required
def vendor_events(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    # Get events from bookings
    bookings = Booking.objects.filter(vendor_id=vendor_id).select_related('event', 'store')
    events = Event.objects.filter(bookings__vendor_id=vendor_id).distinct().order_by('-date')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        events = events.filter(status=status_filter)
    
    return render(request, 'vendor/events.html', {
        'events': events,
        'bookings': bookings,
        'status_filter': status_filter,
        'vendor': vendor,
    })


@vendor_required
def vendor_chat(request):
    vendor_id = request.session.get('user_id')
    vendor = User.objects.get(id=vendor_id)

    # Annotate unread counts
    chats = Chat.objects.filter(vendor_id=vendor_id).select_related('user', 'store')
    chats = chats.annotate(unread_count=Count('messages', filter=Q(messages__is_read=False)))

    return render(request, 'vendor/chat.html', {
        'chats': chats,
        'vendor': vendor,
    })


@vendor_required
def vendor_chat_detail(request, chat_id):
    vendor_id = request.session.get('user_id')
    vendor = User.objects.get(id=vendor_id)

    chat = get_object_or_404(Chat, id=chat_id, vendor_id=vendor_id)

    if request.method == 'POST':
        message_text = request.POST.get('message')
        if message_text:
            ChatMessage.objects.create(
                chat=chat,
                sender=vendor,
                message=message_text
            )
        return redirect('vendor_chat_detail', chat.id)

    # Mark other user's unread messages as read
    chat.messages.filter(is_read=False).exclude(sender_id=vendor_id).update(is_read=True)

    messages_qs = chat.messages.select_related('sender').all()

    return render(request, 'vendor/chat_detail.html', {
        'chat': chat,
        'messages': messages_qs,
        'vendor': vendor,
    })


@vendor_required
def change_password(request):
    vendor_id = request.session.get('user_id')
    vendor = User.objects.get(id=vendor_id)

    if request.method == 'POST':
        old = request.POST.get('current_password') or request.POST.get('old_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')

        if not old or not new or not confirm:
            messages.error(request, 'All fields are required')
        elif old != (vendor.password or ''):
            messages.error(request, 'Current password is incorrect')
        elif new != confirm:
            messages.error(request, 'New passwords do not match')
        else:
            vendor.password = new
            vendor.save()
            messages.success(request, 'Password changed successfully')
            return redirect('vendor_settings')

    return render(request, 'vendor/change_password.html', {
        'vendor': vendor,
    })


@vendor_required
def vendor_earnings(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    earnings = VendorEarning.objects.filter(vendor_id=vendor_id).select_related(
        'booking', 'booking__event', 'booking__store'
    ).order_by('-created_at')
    
    # Filter by payment status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        earnings = earnings.filter(payment_status=status_filter)
    
    # Summary statistics
    total_earned = earnings.filter(payment_status=Payment.STATUS_SUCCESS).aggregate(
        total=Sum('net_amount')
    )['total'] or Decimal('0.00')
    
    pending_amount = earnings.filter(payment_status=Payment.STATUS_PENDING).aggregate(
        total=Sum('net_amount')
    )['total'] or Decimal('0.00')
    
    return render(request, 'vendor/earnings.html', {
        'earnings': earnings,
        'total_earned': total_earned,
        'pending_amount': pending_amount,
        'status_filter': status_filter,
        'vendor': vendor,
    })


@vendor_required
def vendor_payments(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    # Get payments related to vendor's bookings
    bookings = Booking.objects.filter(vendor_id=vendor_id).values_list('id', flat=True)
    earnings = VendorEarning.objects.filter(
        vendor_id=vendor_id,
        booking_id__in=bookings
    ).select_related('booking', 'booking__event').order_by('-created_at')
    
    return render(request, 'vendor/payments.html', {
        'earnings': earnings,
        'vendor': vendor,
    })


@vendor_required
def vendor_reviews(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    # Get reviews for events that have bookings with this vendor
    bookings = Booking.objects.filter(vendor_id=vendor_id).values_list('event_id', flat=True)
    reviews = Review.objects.filter(
        event_id__in=bookings
    ).select_related('user', 'event').order_by('-created_at')
    
    # Calculate average rating
    if reviews.exists():
        avg_rating = sum(r.rating for r in reviews) / reviews.count()
    else:
        avg_rating = 0
    
    # Calculate rating distribution
    rating_distribution = {}
    for rating in range(5, 0, -1):
        rating_distribution[rating] = reviews.filter(rating=rating).count()
    
    return render(request, 'vendor/reviews.html', {
        'reviews': reviews,
        'avg_rating': avg_rating,
        'total_reviews': reviews.count(),
        'rating_distribution': rating_distribution,
        'vendor': vendor,
    })


@vendor_required
def vendor_settings(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    
    if request.method == "POST":
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        business_logo = request.FILES.get('business_logo')
        
        vendor.fullname = fullname
        vendor.email = email
        if mobile:
            vendor.mobile = mobile
        if business_logo:
            vendor.business_logo = business_logo
        vendor.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('vendor_settings')
    
    return render(request, 'vendor/settings.html', {
        'vendor': vendor,
    })


@vendor_required
def vendor_profile(request):
    vendor_id = request.session.get("user_id")
    vendor = User.objects.get(id=vendor_id)
    
    if request.method == "POST":
        fullname = request.POST.get('fullname')
        email = request.POST.get('email')
        mobile = request.POST.get('mobile')
        business_logo = request.FILES.get('business_logo')
        
        vendor.fullname = fullname
        vendor.email = email
        if mobile:
            vendor.mobile = mobile
        if business_logo:
            vendor.business_logo = business_logo
        vendor.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('vendor_dashboard')
    
    return render(request, 'vendor/profile.html', {
        'vendor': vendor,
    })


@vendor_required
def vendor_gallery(request):
    """Manage store images: upload and delete."""
    vendor_id = request.session.get('user_id')
    vendor = User.objects.get(id=vendor_id)
    stores = Store.objects.filter(vendor_id=vendor_id)

    # Handle POST actions: upload or delete
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'upload':
            store_id = request.POST.get('store_id')
            files = request.FILES.getlist('images')
            try:
                store = stores.get(id=store_id)
            except Store.DoesNotExist:
                messages.error(request, 'Invalid store selected!')
                return redirect('vendor_gallery')

            for f in files:
                StoreImage.objects.create(store=store, image=f)
            messages.success(request, 'Images uploaded successfully!')
            return redirect('vendor_gallery')

        if action == 'delete':
            image_id = request.POST.get('image_id')
            try:
                img = StoreImage.objects.get(id=image_id, store__vendor_id=vendor_id)
                img.delete()
                messages.success(request, 'Image deleted successfully!')
            except StoreImage.DoesNotExist:
                messages.error(request, 'Image not found!')
            return redirect('vendor_gallery')

    images = StoreImage.objects.filter(store__vendor_id=vendor_id).select_related('store')

    # Organize images by store name for the template
    images_by_store = {}
    for img in images:
        images_by_store.setdefault(img.store.store_name, []).append(img)

    return render(request, 'vendor/gallery.html', {
        'stores': stores,
        'images_by_store': images_by_store,
        'vendor': vendor,
    })


def store_detail(request, store_id):
    """Public store detail page for users to view a store and its services."""
    try:
        store = Store.objects.select_related('category', 'vendor').get(id=store_id, status=True)
    except Store.DoesNotExist:
        return render(request, 'user/404.html', status=404)

    services = Service.objects.filter(store_id=store_id, is_active=True)

    return render(request, 'user/store_detail.html', {
        'store': store,
        'services': services,
    })


def stores_list(request):
    """Public listing of all active stores for users."""
    stores = Store.objects.filter(status=True).select_related('vendor', 'category').order_by('store_name')
    return render(request, 'user/stores_list.html', {
        'stores': stores,
    })
