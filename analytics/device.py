"""
Lightweight User-Agent classification - no external dependency (a full
UA-parsing library is overkill for "desktop vs mobile vs tablet vs bot").
Good enough for dashboard reporting; not meant to be forensically precise.
"""
import re

_BOT_PATTERN = re.compile(
    r'bot|crawl|spider|slurp|facebookexternalhit|whatsapp|telegrambot|'
    r'discordbot|pingdom|uptimerobot|ahrefsbot|semrushbot|mj12bot',
    re.IGNORECASE,
)
_TABLET_PATTERN = re.compile(r'ipad|tablet', re.IGNORECASE)
_MOBILE_PATTERN = re.compile(
    r'mobile|iphone|ipod|android|blackberry|windows phone|opera mini',
    re.IGNORECASE,
)

# Order matters - checked top to bottom, first match wins. Edge and Opera
# both include "Chrome" in their UA string (Chromium-based), so they have
# to be checked before the generic Chrome pattern; same for Chrome vs Safari
# (Chrome's UA also contains "Safari").
_BROWSER_PATTERNS = [
    ('Edge', re.compile(r'edg/|edge/', re.IGNORECASE)),
    ('Opera', re.compile(r'opr/|opera', re.IGNORECASE)),
    ('Samsung Internet', re.compile(r'samsungbrowser', re.IGNORECASE)),
    ('Chrome', re.compile(r'chrome/|crios/', re.IGNORECASE)),
    ('Firefox', re.compile(r'firefox/|fxios/', re.IGNORECASE)),
    ('Safari', re.compile(r'safari/', re.IGNORECASE)),
    ('Internet Explorer', re.compile(r'msie |trident/', re.IGNORECASE)),
]


def detect_browser(user_agent):
    if not user_agent:
        return 'Other'
    for name, pattern in _BROWSER_PATTERNS:
        if pattern.search(user_agent):
            return name
    return 'Other'


def detect_device(user_agent):
    if not user_agent:
        return 'other'
    ua = user_agent.strip()
    if _BOT_PATTERN.search(ua):
        return 'bot'
    if _TABLET_PATTERN.search(ua):
        return 'tablet'
    if 'android' in ua.lower() and 'mobile' not in ua.lower():
        # Android tablets identify as "Android" without "Mobile"
        return 'tablet'
    if _MOBILE_PATTERN.search(ua):
        return 'mobile'
    return 'desktop'


def get_client_ip(request):
    """Prefer X-Forwarded-For (set by the Apache/Passenger proxy in front
    of the app - see SECURE_PROXY_SSL_HEADER in settings.py for the same
    pattern), fall back to REMOTE_ADDR for direct/dev connections."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
