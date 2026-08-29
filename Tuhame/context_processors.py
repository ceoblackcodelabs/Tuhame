from django.conf import settings


def carto_api_key(request):
    """Makes CARTO_API_KEY available to every template as `carto_api_key`,
    so each of the site's map pages can append it to CARTO's tile URL
    without every view having to pass it individually. See settings.py
    for what happens when it's left unset."""
    return {'carto_api_key': settings.CARTO_API_KEY}
