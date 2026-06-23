# apps/properties/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from properties.models import (
    Property,
    PropertyImage,
    Unit,
    Booking,
    Amenity,
)

from .models import ViewingSchedule


@admin.register(ViewingSchedule)
class ViewingScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'property_link',
        'full_name',
        'email',
        'phone_number',
        'preferred_date',
        'preferred_time',
        'status_badge',
        'created_at',
        'is_upcoming_indicator'
    ]

    list_filter = [
        'status',
        'preferred_time',
        'preferred_date',
        'created_at',
        'property__property_type',
        'property__city',
    ]

    search_fields = [
        'full_name',
        'email',
        'phone_number',
        'property__title',
        'property__address',
        'notes',
        'special_requests',
    ]

    readonly_fields = [
        'created_at',
        'updated_at',
        'confirmed_at',
        'completed_at',
        'cancelled_at',
    ]

    fieldsets = (
        ('Property Information', {
            'fields': ('property', 'user')
        }),
        ('Contact Details', {
            'fields': ('full_name', 'email', 'phone_number')
        }),
        ('Viewing Details', {
            'fields': ('preferred_date', 'preferred_time', 'special_requests')
        }),
        ('Status & Scheduling', {
            'fields': (
                'status',
                'notes',
                'scheduled_datetime',
                'confirmed_at',
                'completed_at',
                'cancelled_at',
                'cancellation_reason'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['confirm_viewings', 'complete_viewings', 'cancel_viewings']

    def property_link(self, obj):
        """Display property with link to admin change page"""
        url = f"/admin/properties/property/{obj.property.id}/change/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.property.title)
    property_link.short_description = 'Property'
    property_link.admin_order_field = 'property__title'

    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#f59e0b',      # Yellow
            'confirmed': '#10b981',    # Green
            'completed': '#6b7280',    # Gray
            'cancelled': '#ef4444',    # Red
            'no_show': '#8b5cf6',      # Purple
        }
        color = colors.get(obj.status, '#6b7280')
        status_display = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.8rem; font-weight: 500;">{}</span>',
            color,
            status_display
        )
    status_badge.short_description = 'Status'

    def is_upcoming_indicator(self, obj):
        """Show if viewing is upcoming"""
        if obj.status == 'confirmed' and obj.scheduled_datetime:
            if obj.scheduled_datetime > timezone.now():
                return format_html('🔵 Upcoming')
        if obj.status == 'pending':
            return format_html('🟡 Awaiting')
        if obj.status == 'completed':
            return format_html('✅ Done')
        return format_html('—')
    is_upcoming_indicator.short_description = 'Status'

    def confirm_viewings(self, request, queryset):
        """Admin action to confirm selected viewings"""
        count = 0
        for viewing in queryset:
            if viewing.status == 'pending':
                viewing.confirm_viewing()
                count += 1
        self.message_user(request, f'{count} viewing(s) confirmed successfully.')
    confirm_viewings.short_description = 'Confirm selected viewings'

    def complete_viewings(self, request, queryset):
        """Admin action to complete selected viewings"""
        count = 0
        for viewing in queryset:
            if viewing.status == 'confirmed':
                viewing.complete_viewing()
                count += 1
        self.message_user(request, f'{count} viewing(s) marked as completed.')
    complete_viewings.short_description = 'Complete selected viewings'

    def cancel_viewings(self, request, queryset):
        """Admin action to cancel selected viewings"""
        count = 0
        reason = "Cancelled by admin"
        for viewing in queryset:
            if viewing.status in ['pending', 'confirmed']:
                viewing.cancel_viewing(reason)
                count += 1
        self.message_user(request, f'{count} viewing(s) cancelled.')
    cancel_viewings.short_description = 'Cancel selected viewings'

    # Add inline view for property admin
    class ViewingInline(admin.TabularInline):
        model = ViewingSchedule
        fields = ['full_name', 'email', 'phone_number', 'preferred_date', 'status_badge']
        readonly_fields = ['status_badge']
        extra = 0
        can_delete = False

        def status_badge(self, obj):
            """Display status with color coding in inline"""
            colors = {
                'pending': '#f59e0b',
                'confirmed': '#10b981',
                'completed': '#6b7280',
                'cancelled': '#ef4444',
                'no_show': '#8b5cf6',
            }
            color = colors.get(obj.status, '#6b7280')
            return format_html(
                '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.7rem;">{}</span>',
                color,
                obj.get_status_display()
            )
        status_badge.short_description = 'Status'