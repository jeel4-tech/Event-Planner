from django.urls import path
from . import views

app_name = 'user'

urlpatterns = [
    path('', views.user_dashboard, name='user_dashboard'),
    path('details/', views.user_details, name='user_details'),
    path('payments/', views.user_payments, name='user_payments'),
    path('payment/<int:event_id>/', views.make_payment, name='make_payment'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('notifications/', views.user_notifications, name='user_notifications'),
    path('events/', views.user_events, name='user_events'),
    path('events/<int:event_id>/', views.event_detail, name='event_detail'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:event_id>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:event_id>/delete/', views.event_delete, name='event_delete'),
    path('reviews/', views.user_reviews, name='user_reviews'),
    path('reviews/write/', views.review_write_list, name='review_write'),
    path('reviews/add/<int:event_id>/', views.review_create, name='review_create'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('services/', views.services_list, name='services_list'),
    # Stores & bookings
    path('stores/', views.stores_list, name='stores_list'),
    path('store/<int:store_id>/', views.store_detail, name='store_detail'),
    path('store/<int:store_id>/book/', views.create_booking, name='create_booking'),
    path('bookings/', views.user_bookings, name='user_bookings'),
    # Chat with vendors
    path('chat/', views.user_chat, name='user_chat'),
    path('chat/<int:chat_id>/', views.user_chat_detail, name='user_chat_detail'),
    path('store/<int:store_id>/chat/', views.start_chat, name='start_chat'),
]
