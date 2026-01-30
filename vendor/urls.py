from django.urls import path
from .views import vendor_dashboard

urlpatterns = [
    path('', vendor_dashboard, name='vendor_dashboard'),
]
    