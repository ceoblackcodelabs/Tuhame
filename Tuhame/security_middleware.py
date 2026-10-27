"""
Two middlewares that protect EVERY form on the site from one place, so a
new form is covered by default instead of relying on each view remembering:

  RateLimitMiddleware  - throttles unsafe requests (POST/PUT/PATCH/DELETE).
                         Sensitive endpoints get their own stricter rule
                         (settings.RATELIMIT_RULES); everything else falls
                         under a generous default cap.
  FormGuardMiddleware  - honeypot + timing-token check on the public forms
                         listed in settings.FORMGUARD_PATHS.

Limited / rejected requests get a clear message (JSON for fetch/AJAX, a
small HTML page otherwise) - never a stack trace or a silent drop.
"""
import re

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string

from . import formguard, ratelimit

UNSAFE = {'POST', 'PUT', 'PATCH', 'DELETE'}


def wants_json(request):
    accept = request.headers.get('Accept', '')
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in accept
        or request.content_type == 'application/json'
    )


def _respond(request, status, message, retry_after=None):
    if wants_json(request):
        response = JsonResponse({'ok': False, 'error': message}, status=status)
    else:
        response = HttpResponse(
            render_to_string('error_limited.html', {'message': message, 'status': status, 'retry_after': retry_after}, request),
            status=status,
        )
    if retry_after:
        response['Retry-After'] = str(retry_after)
    response['Cache-Control'] = 'no-store'
    return response


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.rules = ratelimit.compile_rules(getattr(settings, 'RATELIMIT_RULES', []))
        self.exempt = [re.compile(p) for p in getattr(settings, 'RATELIMIT_EXEMPT', [])]

    def __call__(self, request):
        if getattr(settings, 'RATELIMIT_ENABLED', True) and request.method in UNSAFE:
            blocked = self.check(request)
            if blocked:
                return blocked
        return self.get_response(request)

    def check(self, request):
        path = request.path
        if any(p.search(path) for p in self.exempt):
            return None
        ip = ratelimit.client_ip(request)
        user = request.user.pk if getattr(request, 'user', None) and request.user.is_authenticated else None

        matched = False
        for name, pattern, limit, window, scope in self.rules:
            if not pattern.search(path):
                continue
            matched = True
            who = f'u{user}' if scope == 'user' and user else ip
            count, wait = ratelimit.hit(f'{name}:{who}', window)
            if count > limit:
                return _respond(
                    request, 429,
                    f'Too many attempts. Please try again in {ratelimit.human_wait(wait)}.', wait,
                )
        if not matched:  # generic safety net for every other form
            limit, window = getattr(settings, 'RATELIMIT_DEFAULT', (60, 300))
            count, wait = ratelimit.hit(f'default:{ip}', window)
            if count > limit:
                return _respond(
                    request, 429,
                    f'Too many requests. Please slow down and try again in {ratelimit.human_wait(wait)}.', wait,
                )
        return None


class FormGuardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.patterns = [re.compile(p) for p in getattr(settings, 'FORMGUARD_PATHS', [])]

    def __call__(self, request):
        if (
            getattr(settings, 'FORMGUARD_ENABLED', True)
            and request.method == 'POST'
            and any(p.search(request.path) for p in self.patterns)
        ):
            ok, reason = formguard.check(request.POST)
            if not ok:
                return _respond(
                    request, 400,
                    'We could not verify this submission. Please reload the page and try again.',
                )
        return self.get_response(request)
