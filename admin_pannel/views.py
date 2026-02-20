from django.shortcuts import render, redirect
from account.models import Role, User
from functools import wraps
from vendor.models import category, Store

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
    


# 🏠 Admin Dashboard
@check_admin_session
def admin_dashboard(request):
    user_id = request.session.get('user_id')
    admin = User.objects.filter(id=user_id).first()
    
    from django.utils import timezone
    from user.models import Event
    from vendor.models import Store
    
    now = timezone.now()

    # Calculate stats
    total_users = User.objects.filter(role__name__iexact='user').count()
    active_vendors = User.objects.filter(role__name__iexact='vendor', is_active=True).count()
    pending_vendors = User.objects.filter(role__name__iexact='vendor', is_active=False).count()
    
    total_events = Event.objects.count()
    total_stores = Store.objects.count()
    
    # New stats for dashboard cards
    upcoming_events = Event.objects.filter(date__gte=now).count()
    pending_events = Event.objects.filter(status=Event.STATUS_PENDING).count()

    # Recent 5 events
    recent_events = Event.objects.order_by('-created_at')[:5]

    return render(request, 'admin/dashboard.html', {
        'admin': admin,
        'total_users': total_users,
        'total_vendors': active_vendors,
        'active_vendors': active_vendors,
        'pending_vendors': pending_vendors,
        'total_events': total_events,
        'total_stores': total_stores,
        'upcoming_events': upcoming_events,
        'pending_events': pending_events,
        'recent_events': recent_events,
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

@check_admin_session
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')

        if name:
            category.objects.create(name=name)
            return redirect('manage_categories')

    return render(request, 'admin/add_category.html')