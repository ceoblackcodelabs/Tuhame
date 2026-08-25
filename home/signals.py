# home/signals.py
#
# The owner hero-slideshow pool (home/portfolio.py) is cached for
# HERO_POOL_TTL (1 hour) per owner. Left to expire purely on TTL, a newly
# uploaded property photo - or a property being deactivated/deleted - can
# take up to an hour to show up (or disappear) on that owner's public
# profile, which looks like a bug to the owner even though it's just cache
# lag. Invalidating on save/delete makes changes visible immediately
# instead of waiting out the TTL.
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from properties.models import Property


@receiver([post_save, post_delete], sender=Property)
def invalidate_owner_hero_pool(sender, instance, **kwargs):
    cache.delete(f'owner-hero-pool:{instance.owner_id}')
