
from django.urls import path
from .views import admin_dashboard, manage_users, manage_guests, manage_vendors
urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('manage-users/', manage_users, name='manage_users'),
    path('manage-guests/', manage_guests, name='manage_guests'),
    path('manage-vendors/', manage_vendors, name='manage_vendors'),
]
