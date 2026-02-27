from django.shortcuts import render, redirect
from django.http import HttpResponse
import csv
from django.db import models
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from account.models import Role, User
from functools import wraps
from django.db.models import Sum, Count
from vendor.models import category, Store, Booking

from user.models import Profile, Event, Payment, Review, EventGuestAccess

# 🔐 Admin session decorator
def check_admin_session(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        role = request.session.get('role')

        # hard validation
        if not isinstance(user_id, int) or role != 'admin':
            request.session.flush()
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper

# 👤 Admin View User Details
@check_admin_session
def admin_view_user(request, user_id):
    user = User.objects.filter(id=user_id, role__name__iexact='user').first()
    if not user:
        return redirect('manage_users')

    profile = Profile.objects.filter(user=user).first()
    events = Event.objects.filter(owner=user)
    bookings = Booking.objects.filter(customer=user)
    total_payments = Payment.objects.filter(user=user, status=Payment.STATUS_SUCCESS).aggregate(total=models.Sum('amount'))['total'] or 0

    return render(request, 'admin/user_details.html', {
        'user': user,
        'profile': profile,
        'events': events,
        'bookings': bookings,
        'total_payments': total_payments,
    })


@check_admin_session
def activate_vendor(request, vendor_id):
    """Approve (activate) or deactivate a vendor account."""
    if request.method != 'POST':
        return redirect('manage_vendors')
    vendor = User.objects.filter(id=vendor_id, role__name__iexact='vendor').first()
    if not vendor:
        return redirect('manage_vendors')
    action = request.POST.get('action')
    if action == 'approve':
        vendor.is_active = True
        vendor.save()
    elif action == 'deactivate':
        vendor.is_active = False
        vendor.save()
    return redirect('manage_vendors')


@check_admin_session
def admin_view_vendor(request, vendor_id):
    vendor = User.objects.filter(id=vendor_id, role__name__iexact='vendor').first()
    if not vendor:
        return redirect('manage_vendors')

    profile = Profile.objects.filter(user=vendor).first()
    stores = Store.objects.filter(vendor=vendor)
    bookings = Booking.objects.filter(vendor=vendor)
    total_earnings = 0
    # total payments for vendor can be derived from bookings/payments if needed

    return render(request, 'admin/user_details.html', {
        'user': vendor,
        'profile': profile,
        'events': [],
        'bookings': bookings,
        'total_payments': total_earnings,
    })


@check_admin_session
def admin_view_guest(request, guest_id):
    guest = User.objects.filter(id=guest_id, role__name__iexact='guest').first()
    if not guest:
        return redirect('manage_guests')

    profile = Profile.objects.filter(user=guest).first()
    events = Event.objects.filter(owner=guest)
    bookings = Booking.objects.filter(customer=guest)
    total_payments = Payment.objects.filter(user=guest, status=Payment.STATUS_SUCCESS).aggregate(total=models.Sum('amount'))['total'] or 0

    return render(request, 'admin/user_details.html', {
        'user': guest,
        'profile': profile,
        'events': events,
        'bookings': bookings,
        'total_payments': total_payments,
    })

# 🏠 Admin Dashboard - FIXED VERSION
@check_admin_session
def admin_dashboard(request):
    user_id = request.session.get('user_id')
    admin = User.objects.filter(id=user_id).first()
    
    # Calculate date ranges
    last_week = timezone.now() - timedelta(days=7)
    next_week = timezone.now() + timedelta(days=7)
    last_month = timezone.now() - timedelta(days=30)
    
    # Get real counts from database
    total_events = Event.objects.count()
    new_events_count = Event.objects.filter(created_at__gte=last_week).count()
    
    active_vendors = User.objects.filter(role__name__iexact='vendor', is_active=True).count()
    new_vendors = User.objects.filter(role__name__iexact='vendor', created_at__gte=last_week).count()
    
    pending_requests = User.objects.filter(role__name__iexact='vendor', is_active=False).count()
    
    upcoming_events = Event.objects.filter(
        date__gte=timezone.now(), 
        date__lte=next_week
    ).count()
    
    # Get recent events (last 5)
    recent_events = Event.objects.all().order_by('-created_at')[:5]
    
    # Get recent vendors (last 5)
    recent_vendors = User.objects.filter(role__name__iexact='vendor').order_by('-created_at')[:5]
    
    # Get recent users (last 5)
    recent_users = User.objects.filter(role__name__iexact='user').order_by('-created_at')[:5]
    
    # Get totals for additional stats - FIXED: Changed 'created_at' to 'payment_date'
    total_revenue = Payment.objects.filter(status=Payment.STATUS_SUCCESS).aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Calculate revenue growth (compare with previous month) - FIXED: Changed 'created_at' to 'payment_date'
    previous_month_revenue = Payment.objects.filter(
        status=Payment.STATUS_SUCCESS, 
        payment_date__lte=last_month
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    if previous_month_revenue > 0:
        revenue_growth = round(((total_revenue - previous_month_revenue) / previous_month_revenue) * 100, 1)
    else:
        revenue_growth = 0
    
    total_bookings = Booking.objects.count()
    new_bookings = Booking.objects.filter(created_at__gte=last_week).count()
    
    categories_count = category.objects.count()

    return render(request, 'admin/dashboard.html', {
        'admin': admin,
        # Stats cards data
        'total_events': total_events,
        'new_events_count': new_events_count,
        'active_vendors': active_vendors,
        'new_vendors': new_vendors,
        'pending_requests': pending_requests,
        'upcoming_events': upcoming_events,
        # Recent data
        'recent_events': recent_events,
        'recent_vendors': recent_vendors,
        'recent_users': recent_users,
        # Additional stats
        'total_revenue': total_revenue,
        'revenue_growth': revenue_growth,
        'total_bookings': total_bookings,
        'new_bookings': new_bookings,
        'categories_count': categories_count,
    })

# 👥 Manage Users (Admin Only)
@check_admin_session
def manage_users(request):
    users = User.objects.filter(role__name__iexact='user')

    return render(request, 'admin/manage_user.html', {
        'users': users
    })

# 👥 Manage Guests (Admin Only) — shows photographer-generated guest credentials
@check_admin_session
def manage_guests(request):
    guest_credentials = (
        EventGuestAccess.objects
        .select_related('event', 'vendor', 'created_by', 'event__owner')
        .order_by('-created_at')
    )
    total = guest_credentials.count()
    active_count = guest_credentials.filter(is_active=True).count()
    return render(request, 'admin/manage_guest.html', {
        'guest_credentials': guest_credentials,
        'total': total,
        'active_count': active_count,
    })

# 👥 Manage Vendors (Admin Only)
@check_admin_session
def manage_vendors(request):
    vendors = User.objects.filter(role__name__iexact='vendor')

    return render(request, 'admin/manage_vendor.html', {
        'vendors': vendors
    })


@check_admin_session
def manage_events(request):
    events = Event.objects.select_related('owner').order_by('-created_at')
    return render(request, 'admin/manage_events.html', {
        'events': events
    })


@check_admin_session
def manage_reviews(request):
    reviews = Review.objects.select_related('user', 'event').order_by('-created_at')
    return render(request, 'admin/manage_reviews.html', {
        'reviews': reviews
    })


@check_admin_session
def settings_view(request):
    # simple settings placeholder — implement actual settings logic as needed
    if request.method == 'POST':
        # process settings form if provided
        pass
    return render(request, 'admin/settings.html')


@check_admin_session
def analytics_view(request):
    # lightweight analytics placeholder
    data = {
        'total_events': Event.objects.count(),
        'total_reviews': Review.objects.count(),
        'total_vendors': User.objects.filter(role__name__iexact='vendor').count(),
    }
    return render(request, 'admin/analytics.html', {
        'data': data
    })


@check_admin_session
def events_export(request):
    """Export all events as CSV."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="events.csv"'
    writer = csv.writer(response)
    writer.writerow(['id', 'title', 'date', 'owner_email', 'status'])
    for e in Event.objects.select_related('owner').all().order_by('-created_at'):
        owner_email = getattr(e.owner, 'email', '') if e.owner else ''
        writer.writerow([e.id, e.title, e.date.isoformat(), owner_email, e.status])
    return response


@check_admin_session
def event_create(request):
    """Simple admin event creation form."""
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        date_str = request.POST.get('date')
        owner_id = request.POST.get('owner')
        event_type = request.POST.get('event_type', Event.TYPE_OTHER)
        try:
            owner = User.objects.get(id=int(owner_id)) if owner_id else None
        except Exception:
            owner = None

        if not title:
            return render(request, 'admin/create_event.html', {'error': 'Title is required', 'users': User.objects.all()})

        try:
            from django.utils.dateparse import parse_datetime
            date = parse_datetime(date_str) if date_str else timezone.now()
            if not date:
                date = timezone.now()
        except Exception:
            date = timezone.now()

        Event.objects.create(owner=owner, title=title, date=date, event_type=event_type, status=Event.STATUS_PENDING)
        return redirect('admin_dashboard')

    users = User.objects.filter(role__name__iexact='user')
    return render(request, 'admin/create_event.html', {'users': users})

@check_admin_session
def manage_guest(request):
    guests = User.objects.filter(role__name__iexact='guest')

    return render(request, 'admin/manage_guest.html', {
        'guests': guests
    })

@check_admin_session
def manage_categories(request):
    categories = category.objects.all()

    return render(request, 'admin/manage_category.html', {
        'categories': categories
    })
# Add this to your views.py
@check_admin_session
def admin_view_event(request, event_id):
    event = Event.objects.filter(id=event_id).first()
    if not event:
        return redirect('admin_dashboard')
    
    return render(request, 'admin/event_details.html', {
        'event': event
    })
@check_admin_session
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')

        if name:
            category.objects.create(name=name)
            return redirect('manage_categories')

    return render(request, 'admin/add_category.html')


@check_admin_session
def admin_delete_category(request, category_id):
    if request.method != 'POST':
        return redirect('manage_categories')
    cat = category.objects.filter(id=category_id).first()
    if cat:
        cat.delete()
    return redirect('manage_categories')


@check_admin_session
def admin_view_category(request, category_id):
    cat = category.objects.filter(id=category_id).first()
    if not cat:
        return redirect('manage_categories')
    return render(request, 'admin/category_detail.html', {'category': cat})


@check_admin_session
def admin_delete_review(request, review_id):
    if request.method != 'POST':
        return redirect('admin_manage_reviews')
    rev = Review.objects.filter(id=review_id).first()
    if rev:
        rev.delete()
    return redirect('admin_manage_reviews')


@check_admin_session
def admin_delete_user(request, user_id):
    """Delete a user (admin only). Accepts POST only."""
    if request.method != 'POST':
        return redirect('manage_users')

    user = User.objects.filter(id=user_id).first()
    if not user:
        return redirect('manage_users')

    role_name = user.role.name if user.role else 'user'
    user.delete()

    # Redirect to appropriate listing
    if role_name.lower() == 'vendor':
        return redirect('manage_vendors')
    elif role_name.lower() == 'guest':
        return redirect('manage_guests')
    else:
        return redirect('manage_users')


@check_admin_session
def admin_bookings(request):
    """Platform-wide bookings overview for admin."""
    status_filter = request.GET.get('status', '')
    bookings = Booking.objects.select_related(
        'event', 'store', 'customer', 'vendor'
    ).order_by('-created_at')

    if status_filter:
        bookings = bookings.filter(status=status_filter)

    # Summary counts
    counts = Booking.objects.aggregate(
        total=Count('id'),
        pending=Count('id', filter=models.Q(status='pending')),
        confirmed=Count('id', filter=models.Q(status='confirmed')),
        completed=Count('id', filter=models.Q(status='completed')),
        cancelled=Count('id', filter=models.Q(status='cancelled')),
        revenue=Sum('amount', filter=models.Q(status='completed')),
    )

    return render(request, 'admin/manage_bookings.html', {
        'bookings': bookings,
        'status_filter': status_filter,
        'counts': counts,
        'status_choices': Booking.STATUS_CHOICES,
    })
