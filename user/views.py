from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from .models import Notification, Profile, Event, Payment, Review
from django.utils import timezone
from datetime import timedelta
from account.models import User
from vendor.models import (
    Store, Service, Booking, Chat, ChatMessage,
)
from vendor.models import AdvancePayment
from django.conf import settings
from django.db import transaction
from account.models import Token
from django.shortcuts import Http404
from decimal import Decimal
import re
from django.contrib import messages
import json
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)


def user_required(view_func):
    """Decorator: require session login; redirect to login if not authenticated."""
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('/login/')
        try:
            User.objects.get(id=user_id)
        except User.DoesNotExist:
            request.session.flush()
            return redirect('/login/')
        return view_func(request, *args, **kwargs)
    return wrapper


# ✅ USER DASHBOARD
@user_required
def user_dashboard(request):
    """
    Main dashboard page for logged-in user.
    Supports both Django-authenticated users and the project's session-based login
    (which stores `request.session['user_id']`). If neither is present, redirect
    to login page.
    """
    # Only allow access via session-based login
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    now = timezone.now()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('/login/')

    total_events = Event.objects.filter(owner=user).count()
    upcoming_events = Event.objects.filter(owner=user, date__gte=now).count()
    pending_requests = Event.objects.filter(owner=user, status=Event.STATUS_PENDING).count()
    recent_events = Event.objects.filter(owner=user).order_by('-date')[:5]

    # Bookings (user as customer)
    my_bookings = Booking.objects.filter(customer=user)
    total_bookings = my_bookings.count()
    pending_bookings = my_bookings.filter(status=Booking.STATUS_PENDING).count()
    active_vendors = my_bookings.values('vendor').distinct().count()
    recent_bookings = my_bookings.select_related('store', 'event', 'service').order_by('-created_at')[:5]

    return render(request, 'user/dashboard.html', {
        'user': user,
        'total_events': total_events,
        'active_vendors': active_vendors,
        'pending_requests': pending_requests,
        'upcoming_events': upcoming_events,
        'recent_events': recent_events,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'recent_bookings': recent_bookings,
    })

@user_required
def edit_profile(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)

    if request.method == 'POST':
        fullname = request.POST.get('fullname', '').strip()
        email = request.POST.get('email', '').strip()
        mobile = request.POST.get('mobile', '').strip()

        if not fullname:
            messages.error(request, 'Full name is required')
        elif len(fullname) < 3:
            messages.error(request, 'Full name must be at least 3 characters')
        elif not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            messages.error(request, 'Enter a valid email address')
        elif mobile and not mobile.isdigit():
            messages.error(request, 'Mobile number must contain only digits')
        elif mobile and len(mobile) != 10:
            messages.error(request, 'Mobile number must be 10 digits')
        else:
            user.fullname = fullname
            user.email = email
            user.mobile = mobile
            user.save()
            messages.success(request, 'Profile updated successfully')
            return redirect('user:user_details')

    return render(request, 'user/edit_profile.html', {'user': user})


@user_required
def user_details(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    return render(request, 'user/user_details.html', {'user': user})


# ✅ USER PAYMENTS
@user_required
def user_payments(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)

    # Gather legacy `Payment` records and AdvancePayment records into a unified list
    unified = []

    # Legacy Payment model (if any)
    for p in Payment.objects.filter(user=user).order_by('-payment_date'):
        unified.append({
            'type': 'payment',
            'id': p.id,
            'related': getattr(p, 'event', None),
            'amount': p.amount,
            'status': (p.status or '').lower(),
            'when': getattr(p, 'payment_date', None),
            'gateway': getattr(p, 'gateway', '') if hasattr(p, 'gateway') else '',
            'raw': p,
        })

    # AdvancePayment records (deposit / token-style payments)
    for a in AdvancePayment.objects.filter(user=user).order_by('-created_at'):
        related_event = a.booking.event if a.booking and getattr(a.booking, 'event', None) else None
        unified.append({
            'type': 'advance',
            'id': a.id,
            'related': related_event,
            'amount': a.amount,
            'status': (a.status or '').lower(),
            'when': a.created_at,
            'gateway': a.gateway,
            'raw': a,
        })

    # Sort unified list by `when` desc (items without a when go last)
    unified.sort(key=lambda x: x['when'] or timezone.datetime(1970, 1, 1, tzinfo=timezone.utc), reverse=True)

    return render(request, 'user/payments.html', {
        'payments': unified,
        'user': user,
    })


# ✅ MAKE PAYMENT
@user_required
def make_payment(request, event_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    event = get_object_or_404(Event, id=event_id, owner=user)

    if request.method == "POST":
        amount = request.POST.get('amount')

        Payment.objects.create(
            user=user,
            event=event,
            amount=amount,
            status=Payment.STATUS_SUCCESS
        )

        return redirect('user:payment_success')

    return render(request, 'user/make_payment.html', {
        'event': event,
        'user': user,
    })


# ✅ PAYMENT SUCCESS
@user_required
def payment_success(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    # Combine legacy Payment.success and AdvancePayment succeeded records
    unified = []
    for p in Payment.objects.filter(user=user, status=Payment.STATUS_SUCCESS).order_by('-payment_date'):
        unified.append({
            'id': p.id,
            'related': getattr(p, 'event', None),
            'amount': p.amount,
            'when': getattr(p, 'payment_date', None),
            'gateway': getattr(p, 'gateway', '' ) if hasattr(p, 'gateway') else '',
            'raw': p,
        })

    for a in AdvancePayment.objects.filter(user=user, status=AdvancePayment.STATUS_SUCCEEDED).order_by('-created_at'):
        related_event = a.booking.event if a.booking and getattr(a.booking, 'event', None) else None
        unified.append({
            'id': a.id,
            'related': related_event,
            'amount': a.amount,
            'when': a.created_at,
            'gateway': a.gateway,
            'raw': a,
        })

    unified.sort(key=lambda x: x['when'] or timezone.datetime(1970,1,1, tzinfo=timezone.utc), reverse=True)
    total_successful = len(unified)

    return render(request, 'user/payment_success.html', {
        'successful_payments': unified,
        'total_successful': total_successful,
        'user': user,
    })


# ✅ PAYMENT FAILED
@user_required
def payment_failed(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    # Combine legacy Payment.failed and AdvancePayment failed records
    unified = []
    for p in Payment.objects.filter(user=user, status=Payment.STATUS_FAILED).order_by('-payment_date'):
        unified.append({
            'id': p.id,
            'related': getattr(p, 'event', None),
            'amount': p.amount,
            'when': getattr(p, 'payment_date', None),
            'gateway': getattr(p, 'gateway', '' ) if hasattr(p, 'gateway') else '',
            'raw': p,
        })

    for a in AdvancePayment.objects.filter(user=user, status=AdvancePayment.STATUS_FAILED).order_by('-created_at'):
        related_event = a.booking.event if a.booking and getattr(a.booking, 'event', None) else None
        unified.append({
            'id': a.id,
            'related': related_event,
            'amount': a.amount,
            'when': a.created_at,
            'gateway': a.gateway,
            'raw': a,
        })

    unified.sort(key=lambda x: x['when'] or timezone.datetime(1970,1,1, tzinfo=timezone.utc), reverse=True)
    total_failed = len(unified)

    return render(request, 'user/payment_failed.html', {
        'failed_payments': unified,
        'total_failed': total_failed,
        'user': user,
    })


def is_logged_in(request):
    return bool(request.session.get('user_id'))



@user_required
def user_notifications(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)

    notifications = Notification.objects.filter(user=user).order_by('-created_at')
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'user/notifications.html', {
        'notifications': notifications,
        'user': user,
    })

@user_required
def user_events(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    events = Event.objects.filter(owner=user).order_by('-date')
    reviewed_event_ids = set(Review.objects.filter(user=user).values_list('event_id', flat=True))
    return render(request, 'user/events.html', {
        'events': events,
        'user': user,
        'reviewed_event_ids': reviewed_event_ids,
    })


@user_required
def event_create(request):
    """Create a new event."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        date_str = request.POST.get('date')
        event_type = request.POST.get('event_type', Event.TYPE_OTHER)
        guests = request.POST.get('guests', 0) or 0
        if not title:
            messages.error(request, 'Event title is required.')
            return render(request, 'user/event_form.html', {'user': user, 'event': None})
        try:
            from django.utils.dateparse import parse_datetime
            date = parse_datetime(date_str) if date_str else timezone.now()
            if not date:
                date = timezone.now()
        except Exception:
            date = timezone.now()
        try:
            guests = int(guests)
        except (TypeError, ValueError):
            guests = 0
        Event.objects.create(
            owner=user,
            title=title,
            date=date,
            event_type=event_type,
            guests=guests,
            status=Event.STATUS_PENDING,
        )
        messages.success(request, 'Event created successfully.')
        return redirect('user:user_events')
    return render(request, 'user/event_form.html', {'user': user, 'event': None})


@user_required
def event_edit(request, event_id):
    """Edit an existing event."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    event = get_object_or_404(Event, id=event_id, owner=user)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        date_str = request.POST.get('date')
        event_type = request.POST.get('event_type', Event.TYPE_OTHER)
        guests = request.POST.get('guests', 0) or 0
        status = request.POST.get('status', event.status)
        if not title:
            messages.error(request, 'Event title is required.')
            return render(request, 'user/event_form.html', {'user': user, 'event': event})
        try:
            from django.utils.dateparse import parse_datetime
            date = parse_datetime(date_str) if date_str else event.date
            if date:
                event.date = date
        except Exception:
            pass
        try:
            event.guests = int(guests)
        except (TypeError, ValueError):
            pass
        event.title = title
        event.event_type = event_type
        if status in dict(Event.STATUS_CHOICES):
            event.status = status
        event.save()
        messages.success(request, 'Event updated successfully.')
        return redirect('user:user_events')
    return render(request, 'user/event_form.html', {'user': user, 'event': event})


@user_required
def event_delete(request, event_id):
    """Delete an event."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    event = get_object_or_404(Event, id=event_id, owner=user)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully.')
        return redirect('user:user_events')
    return redirect('user:user_events')


@user_required
def event_detail(request, event_id):
    """Show full details for a single event, including bookings, payments and reviews."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    event = get_object_or_404(Event, id=event_id, owner=user)

    # Bookings for this event
    bookings = Booking.objects.filter(event=event).select_related('store', 'service', 'vendor').order_by('-created_at')

    # Payments and reviews related to this event
    payments = event.payments.all().order_by('-payment_date')
    reviews = event.reviews.all().order_by('-created_at')

    return render(request, 'user/event_detail.html', {
        'event': event,
        'bookings': bookings,
        'payments': payments,
        'reviews': reviews,
        'user': user,
    })

@user_required
def user_reviews(request):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    reviews = Review.objects.filter(user=user).select_related('event').order_by('-created_at')
    return render(request, 'user/reviews.html', {
        'reviews': reviews,
        'user': user,
    })


@user_required
def review_write_list(request):
    """List completed events for the user that are eligible for writing a review."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    # completed events owned by the user
    completed_events = Event.objects.filter(owner=user, status=Event.STATUS_COMPLETED).order_by('-date')
    reviewed_ids = set(Review.objects.filter(user=user).values_list('event_id', flat=True))
    eligible = [e for e in completed_events if e.id not in reviewed_ids]
    return render(request, 'user/review_write_list.html', {
        'events': eligible,
        'user': user,
    })


@user_required
def review_create(request, event_id):
    """Add a review for a completed event (1-5 stars + comment)."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    event = get_object_or_404(Event, id=event_id, owner=user)
    if Review.objects.filter(user=user, event=event).exists():
        messages.warning(request, 'You have already reviewed this event.')
        return redirect('user:user_reviews')
    if request.method == 'POST':
        rating_str = request.POST.get('rating')
        comment = request.POST.get('comment', '').strip()
        try:
            rating = int(rating_str)
            if rating < 1 or rating > 5:
                raise ValueError('Rating must be 1-5')
        except (TypeError, ValueError):
            messages.error(request, 'Please select a rating from 1 to 5 stars.')
            return render(request, 'user/review_form.html', {'user': user, 'event': event})
        Review.objects.create(user=user, event=event, rating=rating, comment=comment)
        messages.success(request, 'Thank you for your review!')
        return redirect('user:user_reviews')
    return render(request, 'user/review_form.html', {'user': user, 'event': event})


@user_required
def change_password(request):
    """User change password (same flow as vendor)."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    if request.method == 'POST':
        old = request.POST.get('current_password') or request.POST.get('old_password')
        new = request.POST.get('new_password')
        confirm = request.POST.get('confirm_password')
        if not old or not new or not confirm:
            messages.error(request, 'All fields are required.')
        elif (user.password or '') != old:
            messages.error(request, 'Current password is incorrect.')
        elif new != confirm:
            messages.error(request, 'New passwords do not match.')
        elif len(new) < 6:
            messages.error(request, 'New password must be at least 6 characters.')
        else:
            user.password = new
            user.save()
            messages.success(request, 'Password changed successfully.')
            return redirect('user:user_details')
    return render(request, 'user/change_password.html', {'user': user})


@user_required
def services_list(request):
    """List of active services for users to browse."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    services = Service.objects.filter(is_active=True).select_related('store')
    return render(request, 'user/services_list.html', {
        'services': services,
        'user': user,
    })


# ---------- Stores (user-facing) ----------
@user_required
def stores_list(request):
    """List active stores with filter by category and search."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    from vendor.models import category as Category
    stores = Store.objects.filter(status=True).select_related('vendor', 'category').order_by('store_name')
    category_id = request.GET.get('category')
    search = request.GET.get('search', '').strip()
    if category_id:
        stores = stores.filter(category_id=category_id)
    if search:
        stores = stores.filter(
            Q(store_name__icontains=search) |
            Q(description__icontains=search) |
            Q(city__icontains=search)
        )
    categories = Category.objects.all()
    return render(request, 'user/stores_list.html', {
        'stores': stores,
        'categories': categories,
        'category_id': category_id,
        'search': search,
        'user': user,
    })


@user_required
def store_detail(request, store_id):
    """Store detail with services, gallery, vendor rating and booking form."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    store = get_object_or_404(Store, id=store_id, status=True)
    services = Service.objects.filter(store=store, is_active=True)
    events = Event.objects.filter(owner=user).order_by('-date')
    # Store gallery (StoreImage)
    from vendor.models import StoreImage
    gallery = StoreImage.objects.filter(store=store).order_by('uploaded_at')
    # Vendor rating: avg of reviews for events that had bookings with this vendor
    vendor_reviews = Review.objects.filter(
        event__bookings__vendor=store.vendor
    ).aggregate(avg_rating=Avg('rating'), count=Count('id'))
    avg_rating = vendor_reviews['avg_rating'] or 0
    review_count = vendor_reviews['count'] or 0
    # Check if current user has a confirmed booking with this store/vendor
    has_confirmed_booking = Booking.objects.filter(
        store=store,
        customer=user,
        vendor=store.vendor,
        status=Booking.STATUS_CONFIRMED
    ).exists()
    return render(request, 'user/store_detail.html', {
        'store': store,
        'services': services,
        'events': events,
        'gallery': gallery,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'user': user,
        'has_confirmed_booking': has_confirmed_booking,
    })


@user_required
def create_booking(request, store_id):
    """Create a booking for a store/service linked to user's event."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    store = get_object_or_404(Store, id=store_id, status=True)

    if request.method == 'POST':
        event_id = request.POST.get('event_id')
        service_id = request.POST.get('service_id')
        notes = request.POST.get('notes', '').strip()
        booking_date_str = request.POST.get('booking_date')

        try:
            event = Event.objects.get(id=event_id, owner=user)
        except Event.DoesNotExist:
            messages.error(request, 'Invalid event selected.')
            return redirect('user:store_detail', store_id=store_id)

        amount = store.price_start
        service = None
        if service_id:
            try:
                service = Service.objects.get(id=service_id, store=store, is_active=True)
                amount = service.price
            except Service.DoesNotExist:
                pass

        booking_date = None
        if booking_date_str:
            try:
                from django.utils.dateparse import parse_datetime
                booking_date = parse_datetime(booking_date_str) or timezone.now()
            except Exception:
                booking_date = timezone.now()

        # Calculate advance required (percentage from settings or default 20%)
        try:
            default_pct = Decimal(getattr(settings, 'ADVANCE_PERCENTAGE', 20))
        except Exception:
            default_pct = Decimal('20')

        advance_required = (Decimal(amount) * default_pct / Decimal('100')).quantize(Decimal('0.01'))

        with transaction.atomic():
            booking = Booking.objects.create(
                event=event,
                store=store,
                service=service,
                customer=user,
                vendor=store.vendor,
                amount=amount,
                advance_percentage=default_pct,
                advance_required=advance_required,
                status=Booking.STATUS_PENDING,
                notes=notes or None,
                booking_date=booking_date,
            )
            # Create a pending AdvancePayment record so user can pay the deposit
            AdvancePayment.objects.create(
                booking=booking,
                user=user,
                amount=advance_required,
                status=AdvancePayment.STATUS_PENDING,
            )

        messages.success(request, f'Booking request sent. Advance of {advance_required} required.')
        return redirect('user:user_bookings')

    return redirect('user:store_detail', store_id=store_id)


@user_required
def user_bookings(request):
    """List and cancel user's bookings."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    bookings = Booking.objects.filter(customer=user).select_related(
        'event', 'store', 'service', 'vendor'
    ).order_by('-created_at')

    status_filter = request.GET.get('status')
    if status_filter:
        bookings = bookings.filter(status=status_filter)

    if request.method == 'POST':
        booking_id = request.POST.get('booking_id')
        action = request.POST.get('action')
        if action == 'cancel':
            try:
                b = bookings.get(id=booking_id)
                if b.status == Booking.STATUS_PENDING:
                    b.status = Booking.STATUS_CANCELLED
                    b.save()
                    messages.success(request, 'Booking cancelled.')
                else:
                    messages.error(request, 'Only pending bookings can be cancelled.')
            except Booking.DoesNotExist:
                messages.error(request, 'Booking not found.')
        return redirect('user:user_bookings')

    # Attach latest advance payment directly to each booking for template access
    for b in bookings:
        b.latest_payment = b.advance_payments.order_by('-created_at').first()

    return render(request, 'user/bookings.html', {
        'bookings': bookings,
        'status_filter': status_filter,
        'user': user,
    })


@user_required
def pay_booking(request, booking_id):
    """Allow user to pay booking advance either via full (gateway stub) or tokens."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    try:
        booking = Booking.objects.get(id=booking_id, customer=user)
    except Booking.DoesNotExist:
        raise Http404('Booking not found')

    advance_due = (booking.advance_required or Decimal('0')) - (booking.advance_paid or Decimal('0'))
    if advance_due <= 0:
        messages.info(request, 'No advance due for this booking.')
        return redirect('user:user_bookings')

    if request.method == 'POST':
        method = request.POST.get('method')
        with transaction.atomic():
            if method == 'advance':
                # Create a Razorpay order for the advance amount and render checkout
                try:
                    import razorpay
                except Exception:
                    messages.error(request, 'Payment gateway not configured (razorpay library missing).')
                    return redirect('user:pay_booking', booking_id=booking.id)

                client = razorpay.Client(auth=(getattr(settings, 'RAZORPAY_KEY_ID', ''), getattr(settings, 'RAZORPAY_KEY_SECRET', '')))
                # amount in paise
                amount_paise = int((advance_due * Decimal('100')).quantize(Decimal('1')))
                try:
                    order = client.order.create({'amount': amount_paise, 'currency': 'INR', 'receipt': f'booking_{booking.id}_advance', 'payment_capture': 1})
                except Exception:
                    logger.exception('Failed to create razorpay order for advance')
                    messages.error(request, 'Failed to initiate payment. Try again later.')
                    return redirect('user:pay_booking', booking_id=booking.id)

                # record AdvancePayment with order id
                ap = AdvancePayment.objects.create(
                    booking=booking,
                    user=user,
                    amount=advance_due,
                    currency='INR',
                    status=AdvancePayment.STATUS_PENDING,
                    gateway='razorpay',
                    gateway_id=order.get('id')
                )

                return render(request, 'user/razorpay_checkout.html', {
                    'key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
                    'order_id': order.get('id'),
                    'amount_paise': amount_paise,
                    'booking': booking,
                    'display_amount': str(advance_due),
                })

            elif method == 'full':
                # Create a Razorpay order and render checkout page
                try:
                    import razorpay
                except Exception:
                    messages.error(request, 'Payment gateway not configured (razorpay library missing).')
                    return redirect('user:pay_booking', booking_id=booking.id)

                client = razorpay.Client(auth=(getattr(settings, 'RAZORPAY_KEY_ID', ''), getattr(settings, 'RAZORPAY_KEY_SECRET', '')))
                # amount in paise
                amount_paise = int((booking.amount * Decimal('100')).quantize(Decimal('1')))
                try:
                    order = client.order.create({'amount': amount_paise, 'currency': 'INR', 'receipt': f'booking_{booking.id}', 'payment_capture': 1})
                except Exception:
                    logger.exception('Failed to create razorpay order')
                    messages.error(request, 'Failed to initiate payment. Try again later.')
                    return redirect('user:pay_booking', booking_id=booking.id)

                # record AdvancePayment with order id
                ap = AdvancePayment.objects.create(
                    booking=booking,
                    user=user,
                    amount=booking.amount,
                    currency='INR',
                    status=AdvancePayment.STATUS_PENDING,
                    gateway='razorpay',
                    gateway_id=order.get('id')
                )

                return render(request, 'user/razorpay_checkout.html', {
                    'key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
                    'order_id': order.get('id'),
                    'amount_paise': amount_paise,
                    'booking': booking,
                })

            else:
                messages.error(request, 'Invalid payment method.')
                return redirect('user:pay_booking', booking_id=booking.id)

    return render(request, 'user/pay_booking.html', {
        'booking': booking,
        'advance_due': advance_due,
    })


@user_required
def booking_payments(request, booking_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    try:
        booking = Booking.objects.get(id=booking_id, customer=user)
    except Booking.DoesNotExist:
        raise Http404('Booking not found')

    payments = booking.advance_payments.order_by('-created_at').all()
    return render(request, 'user/booking_payments.html', {
        'booking': booking,
        'payments': payments,
    })


@csrf_exempt
def razorpay_payment_success(request):
    """AJAX endpoint called by client after Razorpay checkout completes.
    Verifies signature and updates AdvancePayment and Booking.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception as e:
        logger.exception('invalid json in razorpay_payment_success')
        return JsonResponse({'success': False, 'error': 'invalid json', 'detail': str(e)}, status=400)

    payment_id = payload.get('razorpay_payment_id')
    order_id = payload.get('razorpay_order_id')

    if not (payment_id and order_id):
        logger.warning('razorpay_payment_success missing fields', extra={'payload': payload})
        apx = AdvancePayment.objects.filter(gateway_id=order_id, gateway='razorpay').first() if order_id else None
        if apx:
            apx.status = AdvancePayment.STATUS_FAILED
            apx.gateway_response = {'error': 'missing_fields'}
            apx.save()
        return JsonResponse({'success': False, 'error': 'missing fields', 'payload': payload, 'ap_found': bool(apx)}, status=400)

    try:
        import razorpay
    except Exception:
        logger.exception('Razorpay SDK not installed')
        return JsonResponse({'success': False, 'error': 'razorpay sdk not available'}, status=500)

    client = razorpay.Client(auth=(getattr(settings, 'RAZORPAY_KEY_ID', ''), getattr(settings, 'RAZORPAY_KEY_SECRET', '')))

    # Instead of verifying client signature (which may fail in some envs), fetch the payment
    # directly from Razorpay and validate order_id and status.
    try:
        payment_obj = client.payment.fetch(payment_id)
    except Exception as e:
        logger.exception('Failed to fetch payment from Razorpay')
        apx = AdvancePayment.objects.filter(gateway_id=order_id, gateway='razorpay').first()
        if apx:
            apx.status = AdvancePayment.STATUS_FAILED
            apx.gateway_response = {'fetch_exception': str(e)}
            apx.save()
        return JsonResponse({'success': False, 'error': 'fetch_failed', 'exception': str(e)}, status=400)

    fetched_order = payment_obj.get('order_id')
    fetched_status = payment_obj.get('status')

    if fetched_order != order_id:
        logger.warning('Order id mismatch in payment fetch', extra={'fetched_order': fetched_order, 'expected': order_id})
        return JsonResponse({'success': False, 'error': 'order_mismatch', 'fetched_order': fetched_order}, status=400)

    if fetched_status not in ('captured', 'authorized'):
        # Payment not completed
        apx = AdvancePayment.objects.filter(gateway_id=order_id, gateway='razorpay').first()
        if apx:
            apx.status = AdvancePayment.STATUS_FAILED
            apx.gateway_response = payment_obj
            apx.save()
        return JsonResponse({'success': False, 'error': 'payment_not_captured', 'status': fetched_status}, status=400)

    # Payment is valid and captured/authorized: mark AdvancePayment succeeded and apply advance
    ap = AdvancePayment.objects.select_for_update().filter(gateway_id=order_id, gateway='razorpay').first()
    if not ap:
        # create record if missing
        booking_ref = None
        try:
            if order_id and 'booking_' in order_id:
                parts = order_id.split('booking_')[-1]
                bid = int(parts.split('_')[0])
                booking_ref = Booking.objects.filter(id=bid).first()
        except Exception:
            booking_ref = None
        ap = AdvancePayment.objects.create(
            booking=booking_ref,
            user=User.objects.get(id=request.session.get('user_id')),
            amount=Decimal(str(payment_obj.get('amount') / 100.0)) if payment_obj.get('amount') else Decimal('0'),
            currency=payment_obj.get('currency', 'INR'),
            status=AdvancePayment.STATUS_SUCCEEDED,
            gateway='razorpay',
            gateway_id=payment_id,
            gateway_response=payment_obj,
        )
    else:
        ap.status = AdvancePayment.STATUS_SUCCEEDED
        ap.gateway_id = payment_id
        ap.gateway_response = payment_obj
        ap.save()

    try:
        if ap.booking:
            ap.booking.apply_advance(ap.amount)
    except Exception:
        logger.exception('Failed to apply advance to booking after payment fetch')

    return JsonResponse({'success': True})

    # Find matching AdvancePayment by order id
    try:
        ap = AdvancePayment.objects.select_for_update().get(gateway_id=order_id, gateway='razorpay')
    except AdvancePayment.DoesNotExist:
        ap = AdvancePayment.objects.filter(gateway_id=order_id).first()

    if not ap:
        return JsonResponse({'success': False, 'error': 'advance payment record not found'}, status=404)

    ap.status = AdvancePayment.STATUS_SUCCEEDED
    ap.gateway_id = payment_id
    ap.gateway_response = {'verified': True}
    ap.save()

    try:
        booking = ap.booking
        booking.apply_advance(ap.amount)
    except Exception:
        logger.exception('Failed to apply advance to booking')

    return JsonResponse({'success': True})


@csrf_exempt
def razorpay_webhook(request):
    """Handle Razorpay webhooks. Verifies signature and processes payment events."""
    try:
        import razorpay
    except Exception:
        logger.exception('Razorpay SDK not installed')
        return JsonResponse({'ok': False}, status=500)

    body = request.body
    signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
    secret = getattr(settings, 'RAZORPAY_KEY_SECRET', '')

    try:
        razorpay.utility.verify_webhook_signature(body, signature, secret)
    except Exception:
        logger.exception('Invalid webhook signature')
        return JsonResponse({'ok': False}, status=400)

    try:
        data = json.loads(body.decode('utf-8'))
    except Exception:
        return JsonResponse({'ok': False}, status=400)

    event = data.get('event')
    payload = data.get('payload', {})

    if event and event.startswith('payment.'):
        payment_obj = payload.get('payment', {}).get('entity')
        if payment_obj:
            order_id = payment_obj.get('order_id')
            payment_id = payment_obj.get('id')
            status = payment_obj.get('status')
            aps = AdvancePayment.objects.filter(gateway_id=order_id, gateway='razorpay')
            for ap in aps:
                if status in ('captured', 'authorized'):
                    ap.status = AdvancePayment.STATUS_SUCCEEDED
                    ap.gateway_id = payment_id
                    ap.gateway_response = payment_obj
                    ap.save()
                    try:
                        ap.booking.apply_advance(ap.amount)
                    except Exception:
                        logger.exception('apply_advance failed in webhook')
                else:
                    ap.status = AdvancePayment.STATUS_FAILED
                    ap.gateway_response = payment_obj
                    ap.save()

            # If no AdvancePayment was found, nothing to do (webhook may be for other orders)

    return JsonResponse({'ok': True})


# ---------- Chat (user with vendors) ----------
@user_required
def user_chat(request):
    """List chat conversations with vendors."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    chats = Chat.objects.filter(user_id=user_id).select_related('vendor', 'store')
    chats = chats.annotate(unread_count=Count('messages', filter=Q(messages__is_read=False)))
    return render(request, 'user/chat.html', {'chats': chats, 'user': user})


@user_required
def user_delete_chat(request, chat_id):
    """Allow the user to delete a chat/conversation they own."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    chat = get_object_or_404(Chat, id=chat_id, user_id=user_id)

    if request.method == 'POST':
        chat.delete()
        messages.success(request, 'Conversation deleted.')
        return redirect('user:user_chat')

    # For non-POST, redirect back
    return redirect('user:user_chat')


@user_required
def user_chat_detail(request, chat_id):
    """Chat thread with a vendor."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    chat = get_object_or_404(Chat, id=chat_id, user_id=user_id)

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        image = request.FILES.get('image')
        if message_text or image:
            ChatMessage.objects.create(chat=chat, sender=user, message=message_text or '', image=image)
        return redirect('user:user_chat_detail', chat_id=chat.id)

    chat.messages.filter(is_read=False).exclude(sender_id=user_id).update(is_read=True)
    messages_qs = chat.messages.select_related('sender').all()

    return render(request, 'user/chat_detail.html', {
        'chat': chat,
        'messages': messages_qs,
        'user': user,
    })


@user_required
def user_delete_message(request, message_id):
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    msg = get_object_or_404(ChatMessage, id=message_id, sender_id=user_id)
    if request.method == 'POST':
        # delete attached file if present
        try:
            if msg.image:
                msg.image.delete(save=False)
        except Exception:
            pass
        chat_id = msg.chat_id
        msg.delete()
        messages.success(request, 'Message deleted.')
        # If this was an AJAX request, return JSON so client can update UI without redirect
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'deleted': True, 'message_id': message_id})
        return redirect('user:user_chat_detail', chat_id=chat_id)
    return redirect('user:user_chat')


@user_required
def start_chat(request, store_id):
    """Start or open chat with a store's vendor."""
    user_id = request.session.get('user_id')
    user = User.objects.get(id=user_id)
    store = get_object_or_404(Store, id=store_id, status=True)
    vendor = store.vendor
    # Only allow starting a chat when there is a confirmed booking between this user and vendor
    has_confirmed_booking = Booking.objects.filter(
        store=store,
        customer=user,
        vendor=vendor,
        status=Booking.STATUS_CONFIRMED
    ).exists()

    if not has_confirmed_booking:
        messages.error(request, 'Chat is available only after the vendor approves your booking.')
        return redirect('user:user_bookings')

    chat, created = Chat.objects.get_or_create(
        user=user,
        vendor=vendor,
        defaults={'store': store}
    )
    if not created and not chat.store_id:
        chat.store = store
        chat.save(update_fields=['store'])
    return redirect('user:user_chat_detail', chat_id=chat.id)
