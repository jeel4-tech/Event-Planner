from django.contrib import admin
from django.urls import path,include
from .views import register,login_view


urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
]