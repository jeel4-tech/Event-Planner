from django.urls import path
from .views import (
    guest_dashboard, guest_logout, guest_face_search,
    guest_notifications, guest_notification_preferences,
    guest_chat, guest_chat_detail, guest_start_chat,
)

urlpatterns = [
    path('logout/', guest_logout, name='guest_logout'),
    path('face-search/', guest_face_search, name='guest_face_search'),
    path('notifications/', guest_notifications, name='guest_notifications'),
    path('preferences/', guest_notification_preferences, name='guest_notification_preferences'),
    path('chat/', guest_chat, name='guest_chat'),
    path('chat/start/', guest_start_chat, name='guest_start_chat'),
    path('chat/<int:chat_id>/', guest_chat_detail, name='guest_chat_detail'),
    path('', guest_dashboard, name='guest_dashboard'),
]
