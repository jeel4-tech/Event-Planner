from django.shortcuts import render

# Create your views here.
def guest_dashboard(request):
    return render(request, 'guest/dashboard.html')