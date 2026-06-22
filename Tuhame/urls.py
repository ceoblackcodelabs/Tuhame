# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include('home.urls')),
    path('properties/', include('properties.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('clients/', include('clients.urls')),
    path('report/', include('Report.urls')),
    path('users/', include('users.urls')),
    path('payments/', include('payments.urls')),
    # path('contracts/', include('contracts.urls', namespace='contracts')),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)