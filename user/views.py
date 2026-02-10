from django.shortcuts import render, redirect, get_object_or_404
from .models import Notification, Profile, Event, Payment, Review
from django.utils import timezone
from datetime import timedelta
from account.models import User


# ✅ USER DASHBOARD
def user_dashboard(request):
    """
    Main dashboard page for logged-in user.
    Supports both Django-authenticated users and the project's session-based login
    (which stores `request.session['user_id']`). If neither is present, redirect
    to login page.
    """
    # Only allow access via session-based login
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    now = timezone.now()

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('/login/')

    total_events = Event.objects.filter(owner=user).count()
    upcoming_events = Event.objects.filter(owner=user, date__gte=now).count()
    pending_requests = Event.objects.filter(owner=user, status=Event.STATUS_PENDING).count()
    recent_events = Event.objects.filter(owner=user).order_by('-date')[:5]

    # Active vendors placeholder (no Vendor model yet)
    active_vendors = 0

    return render(request, 'user/dashboard.html', {
        'user': user,
        'total_events': total_events,
        'active_vendors': active_vendors,
        'pending_requests': pending_requests,
        'upcoming_events': upcoming_events,
        'recent_events': recent_events,
    })


# ✅ USER DETAILS PAGE (VIEW ONLY)
def user_details(request):
    """
    Separate page only to VIEW user details.
    Works with Django auth or session-based login.
    """
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('/login/')

    profile, created = Profile.objects.get_or_create(user=user)

    return render(request, 'user/user_details.html', {
        'user': user,
        'profile': profile
    })


# ✅ USER PAYMENT LIS

def user_payments(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('/login/')

    payments = Payment.objects.filter(user=user).order_by('-payment_date')

    return render(request, 'user/payments.html', {
        'payments': payments
    })


# ✅ MAKE PAYMENT
def make_payment(request, event_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        request.session.flush()
        return redirect('/login/')

    event = get_object_or_404(Event, id=event_id, owner=user)

    if request.method == "POST":
        amount = request.POST.get('amount')

        Payment.objects.create(
            user=user,
            event=event,
            amount=amount,
            status=Payment.STATUS_SUCCESS
        )

        return redirect('user:payment_success')

    return render(request, 'user/make_payment.html', {
        'event': event
    })


# ✅ PAYMENT SUCCESS
def payment_success(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    user = User.objects.get(id=user_id)

    successful_payments = Payment.objects.filter(
        user=user,
        status=Payment.STATUS_SUCCESS
    ).order_by('-payment_date')

    total_successful = successful_payments.count()

    return render(request, 'user/payment_success.html', {
        'successful_payments': successful_payments,
        'total_successful': total_successful,
    })


# ✅ PAYMENT FAILED
def payment_failed(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    user = User.objects.get(id=user_id)

    failed_payments = Payment.objects.filter(
        user=user,
        status=Payment.STATUS_FAILED
    ).order_by('-payment_date')

    total_failed = failed_payments.count()

    return render(request, 'user/payment_failed.html', {
        'failed_payments': failed_payments,
        'total_failed': total_failed,
    })


def is_logged_in(request):
    return bool(request.session.get('user_id'))



def user_notifications(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    user = User.objects.get(id=user_id)

    notifications = Notification.objects.filter(
        user=user
    ).order_by('-created_at')

    # Mark all as read
    notifications.filter(is_read=False).update(is_read=True)

    return render(request, 'user/notifications.html', {
        'notifications': notifications
    })

def user_events(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    user = User.objects.get(id=user_id)

    events = Event.objects.filter(owner=user).order_by('-date')

    return render(request, 'user/events.html', {
        'events': events
    })

def user_reviews(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login/')

    user = User.objects.get(id=user_id)

    reviews = Review.objects.filter(user=user).order_by('-created_at')

    return render(request, 'user/reviews.html', {
        'reviews': reviews
    })