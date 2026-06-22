# apps/clients/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Client, ClientType, ClientDocument, Watchlist


class ClientDocumentInline(admin.TabularInline):
    """Inline for client documents"""
    model = ClientDocument
    extra = 1
    fields = ['document_type', 'title', 'file', 'expires_at']
    show_change_link = True


class WatchlistInline(admin.TabularInline):
    """Inline for client watchlist"""
    model = Watchlist
    extra = 1
    fields = ['property', 'notes', 'added_at']
    readonly_fields = ['added_at']
    show_change_link = True


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    """Admin configuration for Client model"""

    # List display
    list_display = [
        'name',
        'client_type',
        'email',
        'phone',
        'city',
        'is_active',
        'joined_date',
        'property_count'
    ]

    # Filters
    list_filter = [
        'client_type',
        'is_active',
        'joined_date',
        'city',
        'state'
    ]

    # Search fields
    search_fields = [
        'name',
        'email',
        'phone',
        'city',
        'state',
        'id_number'
    ]

    # Readonly fields
    readonly_fields = [
        'created_at',
        'updated_at',
        'joined_date',
        'display_id_document'
    ]

    # Fieldsets for organizing the form
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'user',
                'client_type',
                'name',
                'email',
                'phone',
                'alternate_phone'
            )
        }),
        ('Address', {
            'fields': (
                'address',
                'city',
                'state',
                'zip_code'
            )
        }),
        ('Identification', {
            'fields': (
                'id_type',
                'id_number',
                'display_id_document',
                'id_document'
            ),
            'classes': ('collapse',)
        }),
        ('Professional Information', {
            'fields': (
                'occupation',
                'employer',
                'annual_income'
            ),
            'classes': ('collapse',)
        }),
        ('Property Preferences', {
            'fields': (
                'preferred_property_types',
                'budget_min',
                'budget_max',
                'preferred_locations'
            ),
            'classes': ('collapse',)
        }),
        ('Status & Notes', {
            'fields': (
                'is_active',
                'notes'
            )
        }),
        ('Metadata', {
            'fields': (
                'created_by',
                'created_at',
                'updated_at',
                'joined_date'
            ),
            'classes': ('collapse',)
        })
    )

    # Inlines
    inlines = [ClientDocumentInline, WatchlistInline]

    # Actions
    actions = ['activate_clients', 'deactivate_clients']

    # List select related (for performance)
    list_select_related = ['user', 'created_by']

    # Date hierarchy
    date_hierarchy = 'joined_date'

    # Save as
    save_as = True

    # Save on top
    save_on_top = True

    # List per page
    list_per_page = 25

    def property_count(self, obj):
        """Count properties in watchlist"""
        count = obj.watchlist.count()
        if count > 0:
            return format_html('<span class="badge badge-info">{}</span>', count)
        return 0
    property_count.short_description = 'Watchlist Items'
    property_count.admin_order_field = 'watchlist__count'

    def display_id_document(self, obj):
        """Display ID document link"""
        if obj.id_document:
            return format_html(
                '<a href="{}" target="_blank">View Document</a>',
                obj.id_document.url
            )
        return "No document uploaded"
    display_id_document.short_description = 'ID Document'

    def activate_clients(self, request, queryset):
        """Activate selected clients"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} client(s) were successfully activated.')
    activate_clients.short_description = 'Activate selected clients'

    def deactivate_clients(self, request, queryset):
        """Deactivate selected clients"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} client(s) were successfully deactivated.')
    deactivate_clients.short_description = 'Deactivate selected clients'

    def get_queryset(self, request):
        """Optimize queryset with prefetch_related"""
        return super().get_queryset(request).prefetch_related('watchlist')

    def save_model(self, request, obj, form, change):
        """Set created_by when creating new client"""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ClientDocument)
class ClientDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for ClientDocument model"""

    list_display = [
        'title',
        'client_link',
        'document_type',
        'uploaded_at',
        'expires_at',
        'is_expired'
    ]

    list_filter = [
        'document_type',
        'uploaded_at',
        'expires_at'
    ]

    search_fields = [
        'title',
        'client__name',
        'client__email'
    ]

    readonly_fields = ['uploaded_at']

    fieldsets = (
        ('Document Information', {
            'fields': (
                'client',
                'document_type',
                'title',
                'file'
            )
        }),
        ('Validity', {
            'fields': (
                'expires_at',
                'uploaded_at'
            )
        })
    )

    def client_link(self, obj):
        """Link to client admin page"""
        url = reverse('admin:clients_client_change', args=[obj.client.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client.name)
    client_link.short_description = 'Client'
    client_link.admin_order_field = 'client__name'

    def is_expired(self, obj):
        """Check if document is expired"""
        from django.utils import timezone
        if obj.expires_at and obj.expires_at < timezone.now().date():
            return format_html('<span class="badge badge-danger">Expired</span>')
        return format_html('<span class="badge badge-success">Valid</span>')
    is_expired.short_description = 'Status'

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('client')


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    """Admin configuration for Watchlist model"""

    list_display = [
        'client_link',
        'property_link',
        'added_at',
        'notes_preview'
    ]

    list_filter = [
        'added_at',
        'client__client_type'
    ]

    search_fields = [
        'client__name',
        'client__email',
        'property__title',
        'notes'
    ]

    readonly_fields = ['added_at']

    fieldsets = (
        ('Watchlist Item', {
            'fields': (
                'client',
                'property',
                'notes'
            )
        }),
        ('Metadata', {
            'fields': ('added_at',)
        })
    )

    def client_link(self, obj):
        """Link to client admin page"""
        url = reverse('admin:clients_client_change', args=[obj.client.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client.name)
    client_link.short_description = 'Client'
    client_link.admin_order_field = 'client__name'

    def property_link(self, obj):
        """Link to property admin page"""
        url = reverse('admin:properties_property_change', args=[obj.property.pk])
        return format_html('<a href="{}">{}</a>', url, obj.property.title)
    property_link.short_description = 'Property'
    property_link.admin_order_field = 'property__title'

    def notes_preview(self, obj):
        """Preview of notes"""
        return obj.notes[:50] + '...' if len(obj.notes) > 50 else obj.notes
    notes_preview.short_description = 'Notes'

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related('client', 'property')


# Optional: Custom admin site headers
admin.site.site_header = 'Real Estate Management System'
admin.site.site_title = 'Real Estate Admin Portal'
admin.site.index_title = 'Welcome to Real Estate Management'