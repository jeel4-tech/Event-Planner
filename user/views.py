from django.shortcuts import render,redirect

from account.models import User
from django.contrib.auth.decorators import login_required

def user_dashboard(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')
    # 🔹 fetch user details
    user = User.objects.get(id=user_id)

    return render(request, 'user/dashboard.html', {
        'user': user
    })

def profile(request):
    user = request.user   # logged-in user object
    return render(request, "user/profile.html", {
        "user": user
    })