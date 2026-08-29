"""
Backs the hero slideshow on an owner's public profile page
(templates/public_profile/owner_portfolio.html). See spec section 5.

The performance requirement is specific: don't hit the database on every
page load just to pick 3 random property photos. The approach here:

1. Cache a POOL of eligible image URLs per owner (an indexed, limited
   query - only active properties, only ones with a main_image, capped to
   HERO_POOL_SIZE) for HERO_POOL_TTL seconds.
2. On every request, pick a random 3-of-N sample from that already-cached
   pool in memory - no query at all on a cache hit.

This is what makes "every refresh shows a different combination" and
"don't query the database every request" both true at once: the pool
changes rarely (once per TTL window), but which 3 images get shown from
it changes every single request, for free.

The three STATIC_HERO_IMAGES below always show first, regardless of
whether the owner has any listings - so a brand-new owner with zero
photos still gets a full, professional-looking hero instead of a blank
gradient. Once they have listings with photos, up to 3 of their own get
appended after the static ones, for up to 6 slides total.
"""
import random

from django.conf import settings
from django.core.cache import cache

HERO_POOL_TTL = 3600  # 1 hour - long enough to actually save queries, short enough that a newly added listing shows up reasonably soon
HERO_POOL_SIZE = 12   # cache a pool bigger than 3 so repeated visits still see variety
HERO_SLIDE_COUNT = 3

# Always-shown fallback slides - generic, well-lit interiors that work
# under the hero's dark overlay regardless of which owner is viewing.
# Hotlinked from Unsplash (same approach already used for the homepage
# hero and auth pages elsewhere in this codebase).
STATIC_HERO_IMAGES = [
    "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=1600&auto=format&fit=crop&q=80",
    "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1600&auto=format&fit=crop&q=80",
]


def _image_url(stored_path):
    if not stored_path:
        return None
    from django.core.files.storage import default_storage
    return default_storage.url(stored_path)


def get_owner_hero_images(owner_user):
    """Returns the hero slideshow image list for this owner: the 3 static
    fallback photos always first, plus up to HERO_SLIDE_COUNT of the
    owner's own listing photos appended after (if they have any) - so
    the hero never has fewer than 3 slides, and tops out at 6."""
    cache_key = f'owner-hero-pool:{owner_user.id}'
    pool = cache.get(cache_key)

    if pool is None:
        from properties.models import Property
        # Indexed (owner + is_active are both indexed on Property - see
        # properties/models.py), only the one field we need, capped so an
        # owner with hundreds of listings doesn't load them all.
        raw_paths = list(
            Property.objects.filter(owner=owner_user, is_active=True)
            .exclude(main_image='')
            .order_by('-created_at')
            .values_list('main_image', flat=True)[:HERO_POOL_SIZE]
        )
        pool = [_image_url(p) for p in raw_paths if p]
        cache.set(cache_key, pool, HERO_POOL_TTL)

    if not pool:
        return list(STATIC_HERO_IMAGES)

    owner_images = random.sample(pool, min(HERO_SLIDE_COUNT, len(pool)))
    return list(STATIC_HERO_IMAGES) + owner_images

