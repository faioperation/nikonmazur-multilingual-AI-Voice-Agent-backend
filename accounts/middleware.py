from django.utils import timezone
from django.conf import settings


class ActiveUserMiddleware:
    """
    Updates user's last activity on every request.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.user.is_authenticated:
            request.user.last_login = timezone.now()
            request.user.save(update_fields=["last_login"])

        return response
