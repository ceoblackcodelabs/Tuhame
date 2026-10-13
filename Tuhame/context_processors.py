from django.conf import settings


def carto_api_key(request):
    """Makes CARTO_API_KEY available to every template as `carto_api_key`,
    so each of the site's map pages can append it to CARTO's tile URL
    without every view having to pass it individually. See settings.py
    for what happens when it's left unset."""
    return {'carto_api_key': settings.CARTO_API_KEY}


def seo(request):
    """Brand + absolute-URL helpers for every template, so canonical/og/
    schema URLs follow SITE_URL / SITE_NAME from .env instead of being
    hardcoded per template (and a page that doesn't override its canonical
    gets its OWN url, not the homepage's)."""
    site_url = settings.SITE_URL.rstrip('/')
    return {
        'site_name': settings.SITE_NAME,
        'site_url': site_url,
        'page_url': site_url + request.path,
    }
