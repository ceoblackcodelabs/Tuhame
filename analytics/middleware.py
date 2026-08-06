from .device import detect_device, get_client_ip
from .models import PageVisit

# Anything under these prefixes is either an asset, an internal/admin
# surface, or an API-ish endpoint - none of it is "someone visited a page"
# in the sense this dashboard reports on.
_EXCLUDED_PREFIXES = (
    '/static/', '/media/',
    '/admin/', '/dashboard/', '/clients/', '/report/', '/contracts/',
    '/payments/', '/properties/properties/', '/properties/add/',
    '/analytics/',
    '/favicon.ico', '/sitemap.xml', '/robots.txt',
)


class PageVisitMiddleware:
    """
    Logs one PageVisit row per qualifying GET request. Deliberately does
    the minimum possible work in the request path - no geolocation call,
    no heavy parsing - so it can't be the thing that makes a page slow.
    Runs after the response is built (doesn't delay sending it), and any
    failure here is swallowed rather than breaking the actual page.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            self._maybe_log(request, response)
        except Exception:
            # Tracking must never be the reason a real page 500s.
            pass
        return response

    def _should_log(self, request, response):
        if request.method != 'GET':
            return False
        if not (200 <= response.status_code < 400):
            return False
        path = request.path
        if path.startswith(_EXCLUDED_PREFIXES):
            return False
        return True

    def _maybe_log(self, request, response):
        if not self._should_log(request, response):
            return

        if not request.session.session_key:
            request.session.save()

        user_agent = request.META.get('HTTP_USER_AGENT', '')
        device = detect_device(user_agent)

        # Bots inflate every number on the dashboard without representing
        # a real person - track them separately rather than folding them
        # into "visitors".
        PageVisit.objects.create(
            path=request.path[:500],
            session_key=request.session.session_key or '',
            user=request.user if request.user.is_authenticated else None,
            ip_address=get_client_ip(request),
            device_type=device,
            referrer=request.META.get('HTTP_REFERER', '')[:500],
        )
