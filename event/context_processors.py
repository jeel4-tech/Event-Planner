def global_app_info(request):
    return {
        'APP_NAME': 'Planify.Ai',
        'APP_LOGO_TEXT': 'PA',                 # Text logo (initials)
        'APP_LOGO_IMAGE': '/static/images/LOGO.png',   # Image logo (inside static/)
    }


def vendor_stores(request):
    """Provide a list of active stores site-wide for templates (safe if DB unavailable)."""
    try:
        from vendor.models import Store
        stores = Store.objects.filter(status=True).order_by('store_name')
    except Exception:
        stores = []
    return {
        'all_stores': stores
    }


def vendor_is_photographer(request):
    """Check if the logged-in vendor has a photographer store."""
    try:
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        if user_id and role == 'vendor':
            from vendor.models import Store
            is_photographer = Store.objects.filter(
                vendor_id=user_id,
                category__name__icontains='photographer'
            ).exists()
            return {'is_photographer': is_photographer}
    except Exception:
        pass
    return {'is_photographer': False}


def admin_pending_counts(request):
    """Provide pending vendor count for admin sidebar badge."""
    try:
        role = request.session.get('role')
        if role == 'admin':
            from account.models import User
            pending_vendors = User.objects.filter(
                role__name__iexact='vendor', is_active=False
            ).count()
            return {'admin_pending_vendors': pending_vendors}
    except Exception:
        pass
    return {'admin_pending_vendors': 0}


def unread_counts(request):
    """
    Provide unread counters for sidebar badges (safe if DB unavailable).
    Uses session-based login.
    """
    user_id = None
    try:
        user_id = request.session.get('user_id')
    except Exception:
        user_id = None

    unread_notifications = 0
    try:
        if user_id:
            from user.models import Notification
            unread_notifications = Notification.objects.filter(user_id=user_id, is_read=False).count()
    except Exception:
        unread_notifications = 0

    return {
        'unread_notifications': unread_notifications,
    }
