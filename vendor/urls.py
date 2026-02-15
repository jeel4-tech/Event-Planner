from pathlib import Path
from django.urls import path
from .views import vendor_dashboard, vendor_store

urlpatterns = [
    path('', vendor_dashboard, name='vendor_dashboard'),
    path('store/', vendor_store, name='vendor_store'),
]
    