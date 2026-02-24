from django.shortcuts import render, redirect
from django.db import models
from django.utils import timezone
from datetime import timedelta
from account.models import Role, User
from functools import wraps
from vendor.models import category, Store, Booking
from user.models import Profile, Event, Payment, Review

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

# 👥 Manage Guests (Admin Only)
@check_admin_session
def manage_guests(request):
    guests = User.objects.filter(role__name__iexact='guest')

    return render(request, 'admin/manage_guest.html', {
        'guests': guests
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
