from django.urls import path
from .views import guest_dashboard, guest_logout, guest_face_search

urlpatterns = [
    path('logout/', guest_logout, name='guest_logout'),
    path('face-search/', guest_face_search, name='guest_face_search'),
    path('', guest_dashboard, name='guest_dashboard'),
]
