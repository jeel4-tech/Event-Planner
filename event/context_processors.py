def global_app_info(request):
    return {
        'APP_NAME': 'Planify.Ai',
        'APP_LOGO_TEXT': 'PA',                 # Text logo (initials)
        'APP_LOGO_IMAGE': '/static/images/LOGO.png',   # Image logo (inside static/)
    }
