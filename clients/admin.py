# apps/clients/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (Client, ClientType, ClientDocument,
                     Watchlist, Bill, BillCategory, UtilityUsage,
                     Payment)


# Optional: Custom admin site headers
admin.site.site_header = 'Real Estate Management System'
admin.site.site_title = 'Real Estate Admin Portal'
admin.site.index_title = 'Welcome to Real Estate Management'


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

@admin.register(BillCategory)
class BillCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'icon']


class PaymentInline(admin.TabularInline):
    model = Payment
    fields = ['user', 'amount', 'payment_method', 'payment_status', 'paid_at']
    readonly_fields = ['paid_at']
    extra = 0
    can_delete = False


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'property_link',
        'user_link',
        'bill_type_display',
        'amount_display',
        'due_date_display',
        'status_badge',
        'is_paid_indicator',
        'created_at'
    ]

    list_filter = [
        'status',
        'bill_type',
        'is_recurring',
        'due_date',
        'created_at',
        'property__city',
        'property__property_type'
    ]

    search_fields = [
        'description',
        'reference_number',
        'property__title',
        'property__address',
        'user__username',
        'user__email',
    ]

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Bill Information', {
            'fields': (
                'property',
                'user',
                'category',
                'bill_type',
                'description',
                'amount',
                'due_date'
            )
        }),
        ('Status & Payment', {
            'fields': (
                'status',
                'paid_date',
                'reference_number',
                'notes'
            )
        }),
        ('Receipt & Documents', {
            'fields': ('receipt',),
            'classes': ('collapse',)
        }),
        ('Recurring', {
            'fields': ('is_recurring', 'recurrence_interval'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [PaymentInline]

    actions = ['mark_as_paid', 'mark_as_overdue', 'mark_as_pending']

    def property_link(self, obj):
        """Display property with link to admin change page"""
        url = f"/admin/properties/property/{obj.property.id}/change/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.property.title)
    property_link.short_description = 'Property'
    property_link.admin_order_field = 'property__title'

    def user_link(self, obj):
        """Display user with link to admin change page"""
        if obj.user:
            url = f"/admin/auth/user/{obj.user.id}/change/"
            return format_html('<a href="{}" target="_blank">{}</a>', url, obj.user.username)
        return '-'
    user_link.short_description = 'User'

    def bill_type_display(self, obj):
        """Display bill type with icon"""
        icons = {
            'rent': '🏠',
            'water': '💧',
            'electricity': '⚡',
            'internet': '📶',
            'service_charge': '🏢',
            'maintenance': '🔧',
            'security': '🔒',
            'garbage': '🗑',
            'other': '📋',
        }
        icon = icons.get(obj.bill_type, '📋')
        return f"{icon} {obj.get_bill_type_display()}"
    bill_type_display.short_description = 'Bill Type'
    bill_type_display.admin_order_field = 'bill_type'

    def amount_display(self, obj):
        """Display formatted amount"""
        return f"KES {obj.amount:,.2f}"
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'

    def due_date_display(self, obj):
        """Display due date with color coding"""
        if obj.status == 'paid':
            color = '#10b981'
        elif obj.due_date < timezone.now().date():
            color = '#ef4444'
        elif (obj.due_date - timezone.now().date()).days <= 3:
            color = '#f59e0b'
        else:
            color = '#6b7280'

        return format_html(
            '<span style="color: {}; font-weight: 500;">{}</span>',
            color,
            obj.due_date.strftime('%b %d, %Y')
        )
    due_date_display.short_description = 'Due Date'
    due_date_display.admin_order_field = 'due_date'

    def status_badge(self, obj):
        """Display status with color coding"""
        colors = {
            'paid': '#10b981',
            'pending': '#f59e0b',
            'overdue': '#ef4444',
            'cancelled': '#6b7280',
            'processing': '#3b82f6',
        }
        color = colors.get(obj.status, '#6b7280')
        status_display = obj.get_status_display()
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">{}</span>',
            color,
            status_display
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'

    def is_paid_indicator(self, obj):
        """Show paid indicator"""
        if obj.status == 'paid':
            return format_html('✅ Paid')
        return '—'
    is_paid_indicator.short_description = 'Paid'

    def mark_as_paid(self, request, queryset):
        """Admin action to mark bills as paid"""
        count = 0
        for bill in queryset:
            if bill.status != 'paid':
                bill.mark_as_paid()
                count += 1
        self.message_user(request, f'{count} bill(s) marked as paid.')
    mark_as_paid.short_description = 'Mark selected bills as paid'

    def mark_as_overdue(self, request, queryset):
        """Admin action to mark bills as overdue"""
        count = 0
        for bill in queryset:
            if bill.status != 'paid':
                bill.status = 'overdue'
                bill.save()
                count += 1
        self.message_user(request, f'{count} bill(s) marked as overdue.')
    mark_as_overdue.short_description = 'Mark selected bills as overdue'

    def mark_as_pending(self, request, queryset):
        """Admin action to mark bills as pending"""
        count = 0
        for bill in queryset:
            bill.status = 'pending'
            bill.save()
            count += 1
        self.message_user(request, f'{count} bill(s) marked as pending.')
    mark_as_pending.short_description = 'Mark selected bills as pending'


@admin.register(UtilityUsage)
class UtilityUsageAdmin(admin.ModelAdmin):
    list_display = [
        'property_link',
        'utility_type_display',
        'reading_date',
        'current_reading',
        'usage_amount',
        'total_cost_display',
        'created_at'
    ]

    list_filter = [
        'utility_type',
        'reading_date',
        'property__city'
    ]

    search_fields = [
        'property__title',
        'notes',
        'property__address'
    ]

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Utility Information', {
            'fields': ('property', 'bill', 'utility_type', 'reading_date')
        }),
        ('Usage Details', {
            'fields': (
                'current_reading',
                'previous_reading',
                'usage_amount',
                'unit',
                'cost_per_unit',
                'total_cost'
            )
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def property_link(self, obj):
        url = f"/admin/properties/property/{obj.property.id}/change/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.property.title)
    property_link.short_description = 'Property'

    def utility_type_display(self, obj):
        icons = {
            'water': '💧',
            'electricity': '⚡',
            'gas': '🔥',
            'internet': '📶',
            'other': '📋',
        }
        return f"{icons.get(obj.utility_type, '📋')} {obj.get_utility_type_display()}"
    utility_type_display.short_description = 'Utility'

    def total_cost_display(self, obj):
        return f"KES {obj.total_cost:,.2f}"
    total_cost_display.short_description = 'Total Cost'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user_link',
        'bill_link',
        'amount_display',
        'payment_method',
        'payment_status_badge',
        'paid_at',
        'mpesa_code'
    ]

    list_filter = [
        'payment_status',
        'payment_method',
        'paid_at',
        'created_at'
    ]

    search_fields = [
        'user__username',
        'user__email',
        'transaction_id',
        'mpesa_code',
        'bill__description'
    ]

    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'bill', 'amount', 'payment_method')
        }),
        ('Status & Transaction', {
            'fields': (
                'payment_status',
                'transaction_id',
                'mpesa_code',
                'paid_at'
            )
        }),
        ('Receipt', {
            'fields': ('receipt_url', 'notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = f"/admin/auth/user/{obj.user.id}/change/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'

    def bill_link(self, obj):
        url = f"/admin/properties/bill/{obj.bill.id}/change/"
        return format_html('<a href="{}" target="_blank">{}</a>', url, obj.bill)
    bill_link.short_description = 'Bill'

    def amount_display(self, obj):
        return f"KES {obj.amount:,.2f}"
    amount_display.short_description = 'Amount'

    def payment_status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'completed': '#10b981',
            'failed': '#ef4444',
            'refunded': '#8b5cf6',
            'cancelled': '#6b7280',
        }
        color = colors.get(obj.payment_status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 500;">{}</span>',
            color,
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Status'