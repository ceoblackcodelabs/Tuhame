# apps/report/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Report list and generation
    path('', views.ReportListView.as_view(), name='report_list'),
    path('generate/', views.ReportGenerateView.as_view(), name='report_generate'),
    path('daily/', views.DailyReportView.as_view(), name='daily_report'),

    # Report detail and management
    path('<int:pk>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('<int:pk>/delete/', views.ReportDeleteView.as_view(), name='report_delete'),
]