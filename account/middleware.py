from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .models import User as AccountUser


class SessionAuthMiddleware(MiddlewareMixin):
    """Populate `request.user` from `request.session['user_id']`.

    This middleware makes the rest of the codebase work without Django's
    authentication system by ensuring `request.user` is the project `User`
    when a session exists, and an `AnonymousUser` otherwise.
    """

    def process_request(self, request):
        user_id = request.session.get('user_id')
        if user_id:
            try:
                user = AccountUser.objects.get(id=user_id)
                # mark as authenticated for compatibility
                setattr(user, 'is_authenticated', True)
                request.user = user
            except AccountUser.DoesNotExist:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()
