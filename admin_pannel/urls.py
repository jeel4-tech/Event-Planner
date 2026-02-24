
from django.urls import path
from . import views
from .views import (
    add_category,
    admin_dashboard,
    manage_categories,
    manage_users,
    manage_vendors,
    admin_view_user,
    manage_events,
    manage_reviews,
    settings_view,
    analytics_view,
)
urlpatterns = [
    path('', admin_dashboard, name='admin_dashboard'),
    path('manage-users/', manage_users, name='manage_users'),
    path('manage-vendors/', manage_vendors, name='manage_vendors'),
    path('manage-categories/', manage_categories, name='manage_categories'),
    path('add-category/', add_category, name='add_category'),
    path('manage-events/', manage_events, name='admin_manage_events'),
    path('manage-reviews/', manage_reviews, name='admin_manage_reviews'),
    path('settings/', settings_view, name='admin_settings'),
    path('analytics/', analytics_view, name='admin_analytics'),
    path('event/<int:event_id>/', views.admin_view_event, name='admin_view_event'),
    path('user/<int:user_id>/', admin_view_user, name='admin_view_user'),
]
