# apps/payments/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from decimal import Decimal
from .models import Invoice, Payment, LateFee, PaymentStatus, PaymentMethod, PaymentCategory


class PaymentInline(admin.TabularInline):
    """Inline for payments within invoice"""
    model = Payment
    extra = 0
    fields = ['payment_id', 'amount', 'payment_method', 'payment_date', 'status', 'reference_number']
    readonly_fields = ['payment_id', 'created_at']
    show_change_link = True
    can_delete = True
    classes = ['collapse']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin configuration for Invoice model"""

    # List display
    list_display = [
        'invoice_number',
        'client_link',
        'property_link',
        'amount_display',
        'total_amount_display',
        'due_date',
        'status_badge',
        'payment_status',
        'days_overdue'
    ]

    # Filters
    list_filter = [
        'status',
        'category',
        'issue_date',
        'due_date',
        'contract__property__city'
    ]

    # Search fields
    search_fields = [
        'invoice_number',
        'client__name',
        'client__email',
        'property__title',
        'contract__contract_number'
    ]

    # Readonly fields
    readonly_fields = [
        'invoice_number',
        'created_at',
        'total_amount',
        'display_payments_summary',
        'remaining_balance'
    ]

    # Fieldsets
    fieldsets = (
        ('Invoice Information', {
            'fields': (
                'invoice_number',
                'contract',
                'client',
                'property',
                'status',
                'category'
            )
        }),
        ('Amount Details', {
            'fields': (
                'amount',
                'tax_amount',
                'discount_amount',
                'total_amount',
                'display_payments_summary',
                'remaining_balance'
            )
        }),
        ('Dates', {
            'fields': (
                'issue_date',
                'due_date',
                'paid_date',
                'period_start',
                'period_end'
            )
        }),
        ('Additional Information', {
            'fields': (
                'description',
                'created_by',
                'created_at'
            ),
            'classes': ('collapse',)
        })
    )

    # Inlines
    inlines = [PaymentInline]

    # Actions
    actions = ['mark_as_paid', 'mark_as_overdue', 'send_reminder']

    # List select related
    list_select_related = ['client', 'property', 'contract']

    # Date hierarchy
    date_hierarchy = 'issue_date'

    # Save as
    save_as = True

    # Save on top
    save_on_top = True

    # List per page
    list_per_page = 25

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

    def amount_display(self, obj):
        """Display base amount"""
        return format_html('<strong>${}</strong>', obj.amount)
    amount_display.short_description = 'Base Amount'

    def total_amount_display(self, obj):
        """Display total amount"""
        color = 'green' if obj.status == 'paid' else 'red' if obj.status == 'overdue' else 'orange'
        return format_html('<strong style="color: {};">${}</strong>', color, obj.total_amount)
    total_amount_display.short_description = 'Total Amount'

    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            'paid': 'success',
            'pending': 'warning',
            'overdue': 'danger',
            'partial': 'info',
            'refunded': 'secondary',
            'cancelled': 'dark'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'

    def payment_status(self, obj):
        """Show payment progress"""
        total_paid = obj.get_total_paid()
        remaining = obj.get_remaining_balance()
        percentage = (total_paid / obj.total_amount * 100) if obj.total_amount > 0 else 0

        return format_html(
            '''
            <div style="width: 100px;">
                <div class="progress" style="height: 20px;">
                    <div class="progress-bar bg-success" role="progressbar"
                         style="width: {}%;"
                         aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">
                        {:.0f}%
                    </div>
                </div>
                <small>Paid: ${} / ${}</small>
            </div>
            ''',
            percentage, percentage, percentage,
            total_paid, obj.total_amount
        )
    payment_status.short_description = 'Payment Progress'

    def days_overdue(self, obj):
        """Calculate days overdue"""
        if obj.status == 'overdue' and obj.due_date:
            from django.utils import timezone
            days = (timezone.now().date() - obj.due_date).days
            return format_html('<span class="badge badge-danger">{} days</span>', days)
        return '-'
    days_overdue.short_description = 'Days Overdue'

    def display_payments_summary(self, obj):
        """Show payments summary"""
        payments = obj.payments.filter(status='paid')
        if not payments:
            return "No payments recorded"

        total_paid = obj.get_total_paid()
        return format_html(
            '''
            <div>
                <strong>Total Paid: ${}</strong><br>
                <small>Number of  {}</small><br>
                <a href="{}">View all payments</a>
            </div>
            ''',
            total_paid,
            payments.count(),
            f"/admin/payments/payment/?invoice__id__exact={obj.id}"
        )
    display_payments_summary.short_description = 'Payments Summary'

    def remaining_balance(self, obj):
        """Display remaining balance"""
        remaining = obj.get_remaining_balance()
        if remaining <= 0:
            return format_html('<span class="badge badge-success">Fully Paid</span>')
        return format_html('<strong style="color: red;">${}</strong>', remaining)
    remaining_balance.short_description = 'Remaining Balance'

    # Custom actions
    def mark_as_paid(self, request, queryset):
        """Mark selected invoices as paid"""
        updated = 0
        for invoice in queryset:
            if invoice.status != 'paid':
                invoice.status = 'paid'
                from django.utils import timezone
                invoice.paid_date = timezone.now().date()
                invoice.save()
                updated += 1
        self.message_user(request, f'{updated} invoice(s) were marked as paid.')
    mark_as_paid.short_description = 'Mark selected invoices as paid'

    def mark_as_overdue(self, request, queryset):
        """Mark selected invoices as overdue"""
        updated = queryset.update(status='overdue')
        self.message_user(request, f'{updated} invoice(s) were marked as overdue.')
    mark_as_overdue.short_description = 'Mark selected invoices as overdue'

    def send_reminder(self, request, queryset):
        """Send payment reminder (placeholder)"""
        count = queryset.filter(status__in=['pending', 'partial', 'overdue']).count()
        self.message_user(request, f'Reminder sent to {count} client(s). (Email integration pending)')
    send_reminder.short_description = 'Send payment reminder to selected invoices'

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('client', 'property', 'contract').prefetch_related('payments')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin configuration for Payment model"""

    # List display
    list_display = [
        'payment_id',
        'invoice_link',
        'client_link',
        'amount_display',
        'payment_method_badge',
        'payment_date',
        'status_badge',
        'reference_number'
    ]

    # Filters
    list_filter = [
        'payment_method',
        'status',
        'payment_date',
        'processed_by'
    ]

    # Search fields
    search_fields = [
        'payment_id',
        'reference_number',
        'client__name',
        'client__email',
        'invoice__invoice_number'
    ]

    # Readonly fields
    readonly_fields = [
        'payment_id',
        'created_at',
        'display_receipt'
    ]

    # Fieldsets
    fieldsets = (
        ('Payment Information', {
            'fields': (
                'payment_id',
                'invoice',
                'client',
                'amount',
                'payment_method',
                'status'
            )
        }),
        ('Payment Details', {
            'fields': (
                'payment_date',
                'reference_number',
                'receipt_file',
                'display_receipt'
            )
        }),
        ('Additional Information', {
            'fields': (
                'notes',
                'processed_by',
                'created_at'
            ),
            'classes': ('collapse',)
        })
    )

    # List select related
    list_select_related = ['invoice', 'client', 'processed_by']

    # Date hierarchy
    date_hierarchy = 'payment_date'

    # List per page
    list_per_page = 25

    def invoice_link(self, obj):
        """Link to invoice admin page"""
        url = reverse('admin:payments_invoice_change', args=[obj.invoice.pk])
        return format_html('<a href="{}">{}</a>', url, obj.invoice.invoice_number)
    invoice_link.short_description = 'Invoice'
    invoice_link.admin_order_field = 'invoice__invoice_number'

    def client_link(self, obj):
        """Link to client admin page"""
        url = reverse('admin:clients_client_change', args=[obj.client.pk])
        return format_html('<a href="{}">{}</a>', url, obj.client.name)
    client_link.short_description = 'Client'
    client_link.admin_order_field = 'client__name'

    def amount_display(self, obj):
        """Display amount with formatting"""
        return format_html('<strong>${}</strong>', obj.amount)
    amount_display.short_description = 'Amount'

    def payment_method_badge(self, obj):
        """Display payment method as badge"""
        colors = {
            'cash': 'success',
            'bank_transfer': 'primary',
            'credit_card': 'info',
            'debit_card': 'info',
            'check': 'warning',
            'online': 'dark'
        }
        color = colors.get(obj.payment_method, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_payment_method_display())
    payment_method_badge.short_description = 'Payment Method'

    def status_badge(self, obj):
        """Display status as badge"""
        colors = {
            'paid': 'success',
            'pending': 'warning',
            'overdue': 'danger',
            'partial': 'info',
            'refunded': 'secondary',
            'cancelled': 'dark'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Status'

    def display_receipt(self, obj):
        """Display receipt link"""
        if obj.receipt_file:
            return format_html(
                '<a href="{}" target="_blank" class="button">View Receipt</a>',
                obj.receipt_file.url
            )
        return "No receipt uploaded"
    display_receipt.short_description = 'Receipt'


@admin.register(LateFee)
class LateFeeAdmin(admin.ModelAdmin):
    """Admin configuration for LateFee model"""

    list_display = [
        'invoice_link',
        'amount_display',
        'days_late',
        'calculated_at',
        'waived_badge'
    ]

    list_filter = [
        'waived',
        'calculated_at'
    ]

    search_fields = [
        'invoice__invoice_number',
        'invoice__client__name'
    ]

    readonly_fields = ['calculated_at']

    fieldsets = (
        ('Late Fee Information', {
            'fields': (
                'invoice',
                'amount',
                'days_late',
                'calculated_at'
            )
        }),
        ('Waiver Information', {
            'fields': (
                'waived',
                'waiver_reason'
            )
        })
    )

    def invoice_link(self, obj):
        """Link to invoice admin page"""
        url = reverse('admin:payments_invoice_change', args=[obj.invoice.pk])
        return format_html('<a href="{}">{}</a>', url, obj.invoice.invoice_number)
    invoice_link.short_description = 'Invoice'

    def amount_display(self, obj):
        """Display amount"""
        return format_html('<strong>${}</strong>', obj.amount)
    amount_display.short_description = 'Amount'

    def waived_badge(self, obj):
        """Display waived status as badge"""
        if obj.waived:
            return format_html('<span class="badge badge-success">Waived</span>')
        return format_html('<span class="badge badge-danger">Due</span>')
    waived_badge.short_description = 'Status'

    actions = ['waive_fees', 'unwaive_fees']

    def waive_fees(self, request, queryset):
        """Waive selected late fees"""
        updated = queryset.update(waived=True, waiver_reason='Waived by admin')
        self.message_user(request, f'{updated} late fee(s) were waived.')
    waive_fees.short_description = 'Waive selected late fees'

    def unwaive_fees(self, request, queryset):
        """Unwaive selected late fees"""
        updated = queryset.update(waived=False, waiver_reason='')
        self.message_user(request, f'{updated} late fee(s) were unwaived.')
    unwaive_fees.short_description = 'Unwaive selected late fees'
