"""
Rate limiting without extra dependencies, backed by Django's cache (shared
across processes when REDIS_URL or the FileBasedCache in settings.py is in
use). One small counter per (rule, who) with a fixed window.

Who = the client IP by default. REMOTE_ADDR is used unless
RATELIMIT_PROXY_HOPS > 0, in which case the client IP is taken that many
entries from the RIGHT of X-Forwarded-For (the only part a proxy we control
added) - never the left-most value, which any client can forge to dodge a
limit. Behind Passenger/Apache REMOTE_ADDR is already the real client.
"""
import re
import time

from django.conf import settings
from django.core.cache import cache


def client_ip(request):
    hops = getattr(settings, 'RATELIMIT_PROXY_HOPS', 0)
    if hops > 0:
        parts = [p.strip() for p in request.META.get('HTTP_X_FORWARDED_FOR', '').split(',') if p.strip()]
        if len(parts) >= hops:
            return parts[-hops]
    return request.META.get('REMOTE_ADDR') or '0.0.0.0'


def hit(key, window):
    """Count one event for `key` in a fixed `window` (seconds).
    Returns (count_including_this_one, seconds_until_the_window_resets)."""
    now = time.time()
    cache_key = f'rl:{key}'
    state = cache.get(cache_key)
    if not state or state['reset'] <= now:
        state = {'n': 0, 'reset': now + window}
    state['n'] += 1
    cache.set(cache_key, state, max(1, int(state['reset'] - now) + 1))
    return state['n'], max(1, int(state['reset'] - now))


def peek(key):
    """(count, seconds_left) without counting a new event."""
    now = time.time()
    state = cache.get(f'rl:{key}')
    if not state or state['reset'] <= now:
        return 0, 0
    return state['n'], max(1, int(state['reset'] - now))


def reset(key):
    cache.delete(f'rl:{key}')


def human_wait(seconds):
    if seconds < 90:
        return f'{seconds} second{"s" if seconds != 1 else ""}'
    minutes = -(-seconds // 60)
    if minutes < 90:
        return f'{minutes} minutes'
    hours = -(-minutes // 60)
    return f'{hours} hours'


def compile_rules(rules):
    return [(name, re.compile(pattern), limit, window, scope) for name, pattern, limit, window, scope in rules]
