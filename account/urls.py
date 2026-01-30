from django.contrib import admin
from django.urls import path,include
from .views import register,login_view,logout_view, landing_page


urlpatterns = [
    path('register/', register, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('', landing_page, name='landing_page'),
]