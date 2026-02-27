from django.contrib import admin
from django.urls import path
from .views import guest_dashboard, guest_logout

urlpatterns = [
    path('logout/', guest_logout, name='guest_logout'),
    path('', guest_dashboard, name='guest_dashboard'),
]
