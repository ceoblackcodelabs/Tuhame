# config/urls.py
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as serve_static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include('home.urls')),
    path('properties/', include('properties.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('clients/', include('clients.urls')),
    path('report/', include('Report.urls')),
    path('users/', include('users.urls')),
    path('payments/', include('payments.urls')),
    path('contracts/', include('contracts.urls')),
    path('blog/', include('blog.urls')),
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