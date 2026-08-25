# home/media_utils.py
#
# For a small, singular, critical, above-the-fold image - like an owner's
# public-profile avatar/logo, shown in the header of every single page
# view - embedding it as base64 directly in the HTML makes it immune to
# any web-server/CDN/media-routing misconfiguration, at the one-time cost
# of a slightly larger HTML response. Deliberately NOT used for property
# photo galleries or anything large/numerous - only for this one critical
# branding spot.
import base64
import mimetypes

from django.core.cache import cache

DATA_URI_CACHE_TTL = 900  # 15 minutes - short enough that a re-uploaded
                           # avatar shows up promptly, long enough to save
                           # re-reading + re-encoding the file on every request


def file_field_to_data_uri(field_file, cache_ttl=DATA_URI_CACHE_TTL):
    """Returns a data: URI for an ImageField/FileField's current file, or
    '' if it can't be read - callers should fall back to field_file.url
    in that case (see profile_picture_url in home/views.py)."""
    if not field_file:
        return ''

    cache_key = f'data-uri:{field_file.name}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        field_file.open('rb')
        data = field_file.read()
        field_file.close()
    except Exception:
        return ''

    mime, _ = mimetypes.guess_type(field_file.name)
    uri = f"data:{mime or 'image/png'};base64,{base64.b64encode(data).decode()}"
    cache.set(cache_key, uri, cache_ttl)
    return uri
