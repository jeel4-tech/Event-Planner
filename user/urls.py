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
    path('reviews/', views.user_reviews, name='user_reviews'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
]
