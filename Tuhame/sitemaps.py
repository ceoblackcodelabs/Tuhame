from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.db.models import Count, Q

from blog.models import BlogPost
from properties.models import Property, PropertyStatus
from users.models import Profile


class PropertySitemap(Sitemap):
    """Only active, available listings - sold/rented/inactive properties
    shouldn't be indexed as if they're still on the market."""
    changefreq = 'daily'
    priority = 0.8

    def items(self):
        return Property.objects.filter(
            is_active=True, status=PropertyStatus.AVAILABLE
        ).order_by('-created_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('home:about_property', kwargs={'slug': obj.slug})


class OwnerPortfolioSitemap(Sitemap):
    """Public property-owner profiles - each is effectively a standalone
    landing page (see product context: 'a professional public profile that
    works like a mini website'), so these are worth indexing on their own.
    Only owners with at least one active listing are included - an empty
    profile isn't worth submitting for indexing."""
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return Profile.objects.filter(
            role='owner', is_active=True, user__is_active=True
        ).annotate(
            active_listings=Count('user__owned_properties', filter=Q(
                user__owned_properties__is_active=True,
                user__owned_properties__status=PropertyStatus.AVAILABLE,
            ))
        ).filter(active_listings__gt=0).select_related('user').order_by('user__username')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('home:owner_portfolio', kwargs={'username': obj.user.username})


class BlogPostSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.6

    def items(self):
        return BlogPost.objects.filter(is_published=True).order_by('-published_at')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()


class StaticViewSitemap(Sitemap):
    """Marketing/static pages that don't come from a model."""
    changefreq = 'monthly'

    def items(self):
        return [
            'home:home',
            'home:properties',
            'home:property_map',
            'home:contact',
            'home:terms_of_service',
            'home:privacy_policy',
            'blog:blog_list',
        ]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == 'home:home' else 0.5
