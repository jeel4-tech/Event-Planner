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
