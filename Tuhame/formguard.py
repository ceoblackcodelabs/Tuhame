"""
Cheap, dependency-free bot filtering for public forms:

  * a honeypot field real users never see or fill (bots fill every input);
  * a signed timestamp token - a form submitted faster than a human can
    type (or long after the page was issued, or with a forged/missing
    token) is rejected.

Add `{% form_guard %}` (home/templatetags/formguard.py) inside a <form>, and
list its URL pattern in settings.FORMGUARD_PATHS - FormGuardMiddleware then
checks every POST to it, so a view can't forget to.
"""
import time

from django.core import signing

HONEYPOT_FIELD = 'website_url'
TOKEN_FIELD = '_fg'
SALT = 'tuhame.formguard'
MIN_AGE = 2           # seconds - faster than this is a script, not a person
MAX_AGE = 6 * 3600    # seconds - forms left open longer must be reloaded


def issue_token():
    return signing.TimestampSigner(salt=SALT).sign(str(int(time.time())))


def check(post):
    """Returns (ok, reason). `post` is request.POST (or any mapping)."""
    if post.get(HONEYPOT_FIELD):
        return False, 'honeypot'
    token = post.get(TOKEN_FIELD, '')
    if not token:
        return False, 'missing token'
    try:
        value = signing.TimestampSigner(salt=SALT).unsign(token, max_age=MAX_AGE)
        issued = int(value)
    except (signing.BadSignature, signing.SignatureExpired, ValueError):
        return False, 'invalid or expired token'
    if time.time() - issued < MIN_AGE:
        return False, 'submitted too fast'
    return True, ''
