from django.shortcuts import render,redirect

from account.models import User

def user_dashboard(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')

    if not user_id:
        return redirect('login')

    if role != 'user':
        return redirect('login')

    # 🔹 fetch user details
    user = User.objects.get(id=user_id)

    return render(request, 'user/dashboard.html', {
        'user': user
    })
