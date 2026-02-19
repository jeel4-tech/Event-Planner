
from django.urls import path
from .views import add_category, admin_dashboard, manage_categories, manage_users, manage_vendors
urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('manage-users/', manage_users, name='manage_users'),
    path('manage-vendors/', manage_vendors, name='manage_vendors'),
    path('manage-categories/', manage_categories, name='manage_categories'),
    path('add-category/', add_category, name='add_category'),
]
