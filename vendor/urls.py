from pathlib import Path
from django.urls import path
from .views import (
    vendor_dashboard, vendor_store, vendor_services, delete_service,
    vendor_orders, vendor_events, vendor_earnings, vendor_payments,
    vendor_reviews, vendor_settings, vendor_profile, vendor_gallery,
    vendor_chat, vendor_chat_detail, vendor_open_chat_for_booking, vendor_add_extra, change_password,
    vendor_delete_chat, vendor_delete_message, vendor_booking_detail
)
from .views import store_detail, stores_list

urlpatterns = [
    path('', vendor_dashboard, name='vendor_dashboard'),
    path('store/', vendor_store, name='vendor_store'),
    path('store/<int:store_id>/', store_detail, name='store_detail'),
    path('stores/', stores_list, name='stores_list'),
    path('services/', vendor_services, name='vendor_services'),
    path('services/delete/<int:service_id>/', delete_service, name='delete_service'),
    path('orders/', vendor_orders, name='vendor_orders'),
    path('orders/chat/<int:booking_id>/', vendor_open_chat_for_booking, name='vendor_chat_with_booking'),
    path('orders/<int:booking_id>/add-extra/', vendor_add_extra, name='vendor_add_extra'),
    path('orders/<int:booking_id>/', vendor_booking_detail, name='vendor_booking_detail'),
    path('events/', vendor_events, name='vendor_events'),
    path('gallery/', vendor_gallery, name='vendor_gallery'),
    path('chat/', vendor_chat, name='vendor_chat'),
    path('chat/<int:chat_id>/', vendor_chat_detail, name='vendor_chat_detail'),
    path('chat/<int:chat_id>/delete/', vendor_delete_chat, name='vendor_delete_chat'),
    path('chat/message/<int:message_id>/delete/', vendor_delete_message, name='vendor_delete_message'),
    path('earnings/', vendor_earnings, name='vendor_earnings'),
    path('payments/', vendor_payments, name='vendor_payments'),
    path('reviews/', vendor_reviews, name='vendor_reviews'),
    path('settings/', vendor_settings, name='vendor_settings'),
    path('profile/', vendor_profile, name='vendor_profile'),
    path('change-password/', change_password, name='change_password'),
]
