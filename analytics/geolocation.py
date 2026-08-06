"""
Resolves PageVisit.ip_address -> country/city, deliberately NOT during the
request that creates the PageVisit (an external HTTP call in that path
would make every single pageview slower, and be a single point of failure
for the whole site if the geolocation service is ever slow or down).

Instead this runs on-demand from the Traffic dashboard view, resolving a
bounded batch of not-yet-resolved recent visits each time the page loads,
using ip-api.com's free batch endpoint (no signup/API key, up to 100 IPs
per call, ~45 requests/min rate limit on the free tier). This is a
best-effort enrichment - if the service is unreachable, visits simply stay
unresolved and show as "Unknown" in the location table, they don't block
anything else in the dashboard.

If you outgrow the free tier or want offline resolution, swap
_lookup_batch() for a MaxMind GeoLite2 database lookup - nothing else in
this module needs to change.
"""
import logging

import requests
from django.db.models import Q

from .models import PageVisit

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
REQUEST_TIMEOUT = 3  # seconds - fail fast, this must never hang a page load
API_URL = 'http://ip-api.com/batch'


def _is_private_ip(ip):
    return ip is None or ip.startswith(('127.', '10.', '192.168.', '::1')) or ip in ('localhost',)


def resolve_pending_locations(limit=BATCH_SIZE):
    """
    Resolves up to `limit` unresolved PageVisit rows. Returns the number
    resolved. Safe to call on every Traffic dashboard page load - it's a
    no-op once everything recent is already resolved.
    """
    pending = list(
        PageVisit.objects.filter(location_resolved=False)
        .exclude(ip_address__isnull=True)
        .order_by('-visited_at')[:limit]
    )
    if not pending:
        return 0

    # Private/local IPs (dev, internal health checks) will never resolve -
    # mark them resolved with an empty location instead of retrying forever.
    resolvable = [v for v in pending if not _is_private_ip(v.ip_address)]
    unresolvable = [v for v in pending if _is_private_ip(v.ip_address)]
    for v in unresolvable:
        v.location_resolved = True
    if unresolvable:
        PageVisit.objects.bulk_update(unresolvable, ['location_resolved'])

    if not resolvable:
        return len(unresolvable)

    try:
        results = _lookup_batch([v.ip_address for v in resolvable])
    except Exception:
        logger.warning('Geolocation lookup failed - visits stay unresolved for next attempt', exc_info=True)
        return len(unresolvable)

    updated = []
    for visit, result in zip(resolvable, results):
        if result and result.get('status') == 'success':
            visit.country = result.get('country', '') or ''
            visit.city = result.get('city', '') or ''
        visit.location_resolved = True
        updated.append(visit)

    if updated:
        PageVisit.objects.bulk_update(updated, ['country', 'city', 'location_resolved'])

    return len(unresolvable) + len(updated)


def _lookup_batch(ip_list):
    """One call to ip-api.com's batch endpoint for up to 100 IPs."""
    payload = [{'query': ip, 'fields': 'status,country,city'} for ip in ip_list]
    resp = requests.post(API_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()
