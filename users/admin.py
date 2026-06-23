# apps/profiles/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Profile, MoveHistory


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'full_name_display',
        'phone_number',
        'city',
        'country',
        'current_property_link',
        'is_active',
        'created_at'
    ]

    list_filter = [
        'is_active',
        'country',
        'city',
        'preferred_contact_method',
        'preferred_language',
        'created_at'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'full_name',
        'phone_number',
        'address',
        'city',
        'employer'
    ]

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'full_name', 'bio', 'profile_picture', 'date_of_birth')
        }),
        ('Contact Details', {
            'fields': ('phone_number', 'alternative_phone', 'address', 'city', 'state', 'country', 'zip_code')
        }),
        ('Professional Information', {
            'fields': ('occupation', 'employer')
        }),
        ('Current Residence', {
            'fields': ('current_property', 'moved_in_date')
        }),
        ('Emergency Contact', {
            'fields': ('emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relationship')
        }),
        ('Preferences', {
            'fields': ('preferred_contact_method', 'preferred_language', 'email_notifications', 'sms_notifications')
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def full_name_display(self, obj):
        """Display full name"""
        return obj.get_full_name()
    full_name_display.short_description = 'Full Name'
    full_name_display.admin_order_field = 'full_name'

    def current_property_link(self, obj):
        """Display current property with link"""
        if obj.current_property:
            url = f"/admin/properties/property/{obj.current_property.id}/change/"
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                url,
                obj.current_property.title
            )
        return format_html('<span style="color: #999;">No property</span>')
    current_property_link.short_description = 'Current Property'

    actions = ['mark_active', 'mark_inactive']

    def mark_active(self, request, queryset):
        """Mark selected profiles as active"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} profile(s) marked as active.')
    mark_active.short_description = 'Mark selected profiles as active'

    def mark_inactive(self, request, queryset):
        """Mark selected profiles as inactive"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} profile(s) marked as inactive.')
    mark_inactive.short_description = 'Mark selected profiles as inactive'


@admin.register(MoveHistory)
class MoveHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'profile',
        'from_property_title',
        'to_property_title',
        'moved_in_date',
        'moved_out_date',
        'created_at'
    ]

    list_filter = ['moved_in_date', 'moved_out_date']
    search_fields = [
        'profile__full_name',
        'profile__user__username',
        'from_property__title',
        'to_property__title'
    ]

    def from_property_title(self, obj):
        return obj.from_property.title if obj.from_property else '—'
    from_property_title.short_description = 'From Property'

    def to_property_title(self, obj):
        return obj.to_property.title if obj.to_property else '—'
    to_property_title.short_description = 'To Property'