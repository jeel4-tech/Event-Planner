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
