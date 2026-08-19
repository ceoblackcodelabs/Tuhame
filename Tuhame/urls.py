# config/urls.py
from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as serve_static
from django.views.generic import RedirectView, TemplateView

from .sitemaps import PropertySitemap, BlogPostSitemap, StaticViewSitemap

sitemaps = {
    'properties': PropertySitemap,
    'blog': BlogPostSitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path(
        'robots.txt',
        TemplateView.as_view(template_name='robots.txt', content_type='text/plain'),
        name='robots_txt',
    ),
    # robots.txt already points here (Sitemap: https://2hame.com/sitemap.xml) -
    # this is what actually makes that promise real instead of 404ing.
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    # Google (and many other crawlers/tools) request /favicon.ico at the
    # domain root directly - they don't parse <link rel="icon"> out of
    # <head> for this check. Without this route, that request 404s even
    # though the favicon itself works fine for browsers, which is exactly
    # why Search Console can fail to pick it up while the tab icon looks
    # correct. staticfiles_storage.url() resolves to the same
    # cache-busted, hashed path {% static %} produces elsewhere.
    path(
        'favicon.ico',
        RedirectView.as_view(url=staticfiles_storage.url('assets/images/favicon.ico'), permanent=True),
        name='favicon',
    ),
    path('admin/', admin.site.urls),
    path('analytics/', include('analytics.urls')),
    path("", include('home.urls')),
    path('properties/', include('properties.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('clients/', include('clients.urls')),
    path('report/', include('Report.urls')),
    path('users/', include('users.urls')),
    path('payments/', include('payments.urls')),
    path('contracts/', include('contracts.urls')),
    path('blog/', include('blog.urls')),
    path('settings/', include('subscriptions.urls')),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
]

# Static files: WhiteNoise's middleware already serves these in both dev and
# production, but keeping this here is a harmless no-op safety net.
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Media files (profile pictures, property photos, contracts, ...):
# django.conf.urls.static.static() only ever registers a route when
# DEBUG=True — in production (DEBUG=False) it silently adds nothing, which
# is why uploads succeeded but never displayed on the live site. We serve
# media through Django unconditionally so it works the same in both places.
#
# On shared hosting (cPanel/Passenger) there's no nginx in front of Django
# to hand this off to, so Django serving it directly is the correct simple
# fix here. If you later move to a VPS with nginx, point nginx at /media/
# instead and drop this for better performance.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_static, {'document_root': settings.MEDIA_ROOT}),
]