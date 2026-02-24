
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
    path('events/export/', views.events_export, name='admin_events_export'),
    path('events/new/', views.event_create, name='admin_create_event'),
    path('manage-reviews/', manage_reviews, name='admin_manage_reviews'),
    path('settings/', settings_view, name='admin_settings'),
    path('analytics/', analytics_view, name='admin_analytics'),
    path('event/<int:event_id>/', views.admin_view_event, name='admin_view_event'),
    path('user/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('user/<int:user_id>/', admin_view_user, name='admin_view_user'),
    path('vendor/<int:vendor_id>/', views.admin_view_vendor, name='admin_view_vendor'),
    path('guest/<int:guest_id>/', views.admin_view_guest, name='admin_view_guest'),
    path('category/<int:category_id>/delete/', views.admin_delete_category, name='admin_delete_category'),
    path('category/<int:category_id>/', views.admin_view_category, name='admin_view_category'),
    path('review/<int:review_id>/delete/', views.admin_delete_review, name='admin_delete_review'),
]
