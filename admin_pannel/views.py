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
    

    return render(request, 'admin/dashboard.html', {
        'admin': admin
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