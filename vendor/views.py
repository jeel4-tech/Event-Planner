from django.shortcuts import render, redirect
from account.models import User   

def vendor_dashboard(request):
    user_id = request.session.get('user_id')
    role = request.session.get('role')

    if not user_id:
        return redirect('login')

    if role != 'vendor':
        return redirect('login')

    # 🔹 fetch vendor details
    vendor = User.objects.get(id=user_id)

    return render(request, 'vendor/dashboard.html', {
        'vendor': vendor
    })
