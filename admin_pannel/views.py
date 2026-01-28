from django.shortcuts import redirect, render

from account.models import User

# Create your views here.
def admin_dashboard(request):
    
    user_id = request.session.get('user_id')
    role = request.session.get('role')

    if not user_id:
        return redirect('login')

    if role != 'admin':
        return redirect('login')

    # 🔹 fetch admin details
    admin = User.objects.get(id=user_id)

    return render(request, 'admin/dashboard.html', {
        'admin': admin
    })
