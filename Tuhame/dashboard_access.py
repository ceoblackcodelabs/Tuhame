# Tuhame/dashboard_access.py
"""
Restricts EVERY URL under /dashboard/ to verified property owners.

This is deliberately a middleware rather than a per-view mixin: the
dashboard app currently has one URL, but anything added under
dashboard/urls.py in the future is automatically covered without anyone
having to remember to decorate the new view. It runs after
AuthenticationMiddleware (needs request.user) and before the view.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse


DASHBOARD_PREFIX = '/dashboard/'


class DashboardAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(DASHBOARD_PREFIX) and not self._is_allowed(request.user):
            return self._deny(request)
        return self.get_response(request)

    @staticmethod
    def _is_allowed(user):
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.is_staff:
            return True
        profile = getattr(user, 'profile', None)
        return bool(
            profile
            and profile.role == 'owner'
            and profile.is_verified_owner
        )

    @staticmethod
    def _deny(request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), login_url=settings.LOGIN_URL)

        profile = getattr(request.user, 'profile', None)
        if profile and profile.role == 'owner' and profile.verification_status == 'pending':
            messages.info(
                request,
                "Your property owner verification is still pending review. "
                "You'll get dashboard access as soon as it's approved."
            )
        else:
            messages.warning(
                request,
                "The dashboard is only available to verified property owners. "
                "Switch your role and request verification from your profile."
            )
        return redirect('edit_profile')
