from django.urls import path

from . import views

app_name = 'analytics'

urlpatterns = [
    path('traffic/', views.TrafficDashboardView.as_view(), name='traffic'),
    path('blog/', views.BlogAnalyticsView.as_view(), name='blog_analytics'),
]
