from django.contrib import admin
from django.urls import path
from .views import guest_dashboard

urlpatterns = [
    path('', guest_dashboard, name='guest_dashboard'),
]
