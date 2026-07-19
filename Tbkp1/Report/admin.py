# apps/report/admin.py
from django.contrib import admin
from .models import Report, ReportSchedule


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['report_id', 'title', 'report_type', 'generated_at', 'status']
    list_filter = ['report_type', 'status', 'generated_at']
    search_fields = ['title', 'report_id', 'description']
    readonly_fields = ['report_id', 'generated_at', 'report_data']

    fieldsets = (
        ('Report Information', {
            'fields': ('report_id', 'title', 'description', 'report_type', 'status')
        }),
        ('Period', {
            'fields': ('start_date', 'end_date', 'generated_for_date')
        }),
        ('Statistics', {
            'fields': ('total_properties', 'total_clients', 'total_contracts',
                      'total_revenue', 'pending_invoices', 'overdue_invoices')
        }),
        ('Metadata', {
            'fields': ('generated_by', 'generated_at', 'last_accessed', 'parameters'),
            'classes': ('collapse',)
        })
    )


@admin.register(ReportSchedule)
class ReportScheduleAdmin(admin.ModelAdmin):
    list_display = ['name', 'schedule_type', 'is_active', 'last_run']
    list_filter = ['schedule_type', 'is_active']