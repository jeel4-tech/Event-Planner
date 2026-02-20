
from django.urls import path
from . import views
from .views import add_category, admin_dashboard, manage_categories, manage_users, manage_vendors, admin_view_user
urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('manage-users/', manage_users, name='manage_users'),
    path('manage-vendors/', manage_vendors, name='manage_vendors'),
    path('manage-categories/', manage_categories, name='manage_categories'),
    path('add-category/', add_category, name='add_category'),
    path('event/<int:event_id>/', views.admin_view_event, name='admin_view_event'),
    path('user/<int:user_id>/', admin_view_user, name='admin_view_user'),
]
