from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import User, Role
from user.models import EventGuestAccess
# Note: dashboards are routed by URL name via redirects; no need to import view funcs.

def landing_page(request):
    return render(request, "landing_page.html")
# ---------------- REGISTER ----------------
def register(request):
    # 🚫 hide admin + guest (guest module not used)
    roles = Role.objects.exclude(name__iexact="admin").exclude(name__iexact="guest")

    if request.method == "POST":
        fullname = request.POST.get("fullname")
        email = request.POST.get("email")
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")
        role_id = request.POST.get("role")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect("register")

        try:
            role = Role.objects.get(id=role_id)
        except Role.DoesNotExist:
            messages.error(request, "Invalid role selected")
            return redirect("register")

        User.objects.create(
            fullname=fullname,
            email=email,
            mobile=mobile,
            password=make_password(password),
            role=role
        )

        messages.success(request, "Registration successful")
        return redirect("login")

    return render(request, "accounts/registration.html", {"roles": roles})


# ---------------- LOGIN ----------------
def login_view(request):
    if request.method == "POST":
        email_or_guest_id = request.POST.get("email", "").strip().upper()
        password = request.POST.get("password")

        # Check if it's a Guest ID (format: EVENT-XXXX)
        if email_or_guest_id.startswith("EVENT-"):
            # Guest login
            try:
                access = EventGuestAccess.objects.get(guest_id=email_or_guest_id, is_active=True)
                
                if check_password(password, access.password):
                    # Store guest session
                    request.session['guest_access_id'] = access.id
                    request.session['guest_event_id'] = access.event_id
                    request.session['guest_role'] = 'guest'
                    messages.success(request, f'Welcome! You are now viewing {access.event.title}')
                    return redirect('guest_dashboard')
                else:
                    messages.error(request, 'Invalid password')
            except EventGuestAccess.DoesNotExist:
                messages.error(request, 'Invalid Guest ID')
        else:
            # Regular user/vendor/admin login
            email = email_or_guest_id.lower()
            try:
                user = User.objects.get(email=email)

                if check_password(password, user.password):
                    request.session["user_id"] = user.id
                    request.session["role"] = user.role.name.lower()

                    # 🔁 Role-based redirect
                    if user.role.name.lower() == "admin":
                        return redirect("admin_dashboard")
                    elif user.role.name.lower() == "vendor":
                        return redirect("vendor_dashboard")
                    else:
                        return redirect('/user/')
                else:
                    messages.error(request, "Invalid password")

            except User.DoesNotExist:
                messages.error(request, "User not found")

    return render(request, "accounts/login.html")


# ---------------- LOGOUT ----------------
def logout_view(request):
    request.session.flush()
    return redirect("login")
