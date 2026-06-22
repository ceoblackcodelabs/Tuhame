# apps/payments/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from .models import Invoice, Payment, PaymentStatus, PaymentCategory
from .forms import InvoiceForm, PaymentForm, InvoiceFilterForm, PaymentFilterForm
from django.db import models
from decimal import Decimal


class InvoiceListView(LoginRequiredMixin, ListView):
    model = Invoice
    template_name = 'payments/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 20

    def get_queryset(self):
        queryset = Invoice.objects.all().select_related('client', 'property', 'contract')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Filter by date range
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search) |
                Q(client__name__icontains=search) |
                Q(property__title__icontains=search)
            )

        return queryset.order_by('-issue_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = InvoiceFilterForm(self.request.GET)

        # Statistics
        context['total_invoices'] = Invoice.objects.count()
        context['paid_invoices'] = Invoice.objects.filter(status='paid').count()
        context['pending_invoices'] = Invoice.objects.filter(status='pending').count()
        context['overdue_invoices'] = Invoice.objects.filter(status='overdue').count()

        # Financial totals
        context['total_amount'] = Invoice.objects.aggregate(total=Sum('total_amount'))['total'] or 0
        context['paid_amount'] = Invoice.objects.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
        context['pending_amount'] = Invoice.objects.filter(status='pending').aggregate(total=Sum('total_amount'))['total'] or 0
        context['overdue_amount'] = Invoice.objects.filter(status='overdue').aggregate(total=Sum('total_amount'))['total'] or 0

        return context


class InvoiceDetailView(LoginRequiredMixin, DetailView):
    model = Invoice
    template_name = 'payments/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Calculate payments
        payments = self.object.payments.filter(status='paid')
        total_paid = payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        # Round to 2 decimal places
        total_paid = total_paid.quantize(Decimal('0.01'))
        remaining_balance = (self.object.total_amount - total_paid).quantize(Decimal('0.01'))

        context['payments'] = payments
        context['total_paid'] = total_paid
        context['remaining_balance'] = remaining_balance
        context['can_add_payment'] = self.object.status != 'paid' and remaining_balance > Decimal('0.01')

        # Debug output
        print(f"Invoice {self.object.invoice_number}: Total=${self.object.total_amount}, Paid=${total_paid}, Remaining=${remaining_balance}")

        return context


class InvoiceCreateView(LoginRequiredMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'payments/invoice_form.html'
    success_url = reverse_lazy('invoice_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)

        # Check if invoice is overdue
        if form.instance.due_date < timezone.now().date():
            form.instance.status = 'overdue'
            form.instance.save()

        messages.success(self.request, f'Invoice {form.instance.invoice_number} has been created successfully!')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Invoice'
        context['submit_text'] = 'Create Invoice'
        return context


class InvoiceUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = 'payments/invoice_form.html'
    success_url = reverse_lazy('invoice_list')

    def test_func(self):
        invoice = self.get_object()
        # Allow staff or if invoice is not paid
        return self.request.user.is_staff or invoice.status != 'paid'

    def form_valid(self, form):
        messages.success(self.request, f'Invoice {form.instance.invoice_number} has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Invoice'
        context['submit_text'] = 'Update Invoice'
        return context


class InvoiceDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Invoice
    template_name = 'payments/invoice_confirm_delete.html'
    success_url = reverse_lazy('invoice_list')

    def test_func(self):
        """Check if user has permission to delete"""
        invoice = self.get_object()
        # Only staff can delete invoices, and only if not paid
        return self.request.user.is_staff and invoice.status != 'paid'

    def delete(self, request, *args, **kwargs):
        """Add success message before deletion"""
        invoice = self.get_object()
        invoice_number = invoice.invoice_number
        messages.success(request, f'Invoice {invoice_number} has been deleted successfully!')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add extra context to template"""
        context = super().get_context_data(**kwargs)
        context['object_name'] = 'Invoice'
        return context


class PaymentListView(LoginRequiredMixin, ListView):
    model = Payment
    template_name = 'payments/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20

    def get_queryset(self):
        queryset = Payment.objects.all().select_related('invoice', 'client', 'processed_by')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by payment method
        payment_method = self.request.GET.get('payment_method')
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # Filter by date range
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(payment_id__icontains=search) |
                Q(client__name__icontains=search) |
                Q(invoice__invoice_number__icontains=search) |
                Q(reference_number__icontains=search)
            )

        return queryset.order_by('-payment_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = PaymentFilterForm(self.request.GET)

        # Statistics
        context['total_payments'] = Payment.objects.count()
        context['total_amount'] = Payment.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0

        # Payment method breakdown
        context['payment_methods'] = Payment.objects.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        )

        # Recent payments (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        context['recent_payments'] = Payment.objects.filter(
            payment_date__gte=thirty_days_ago
        ).count()

        return context


class PaymentDetailView(LoginRequiredMixin, DetailView):
    model = Payment
    template_name = 'payments/payment_detail.html'
    context_object_name = 'payment'


class PaymentCreateView(LoginRequiredMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'

    def get_initial(self):
        initial = super().get_initial()
        # If invoice_id is provided in URL, pre-select it
        invoice_id = self.kwargs.get('invoice_id')
        if invoice_id:
            invoice = get_object_or_404(Invoice, pk=invoice_id)
            initial['invoice'] = invoice
        return initial

    def form_valid(self, form):
        # Get the invoice from the form
        invoice = form.cleaned_data.get('invoice')

        # Automatically set the client from the invoice
        form.instance.client = invoice.client

        # Set processed by and status
        form.instance.processed_by = self.request.user
        form.instance.status = 'paid'

        # Save the payment
        response = super().form_valid(form)

        # Update invoice status
        total_paid = invoice.payments.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        total_paid = total_paid.quantize(Decimal('0.01'))
        invoice_total = invoice.total_amount.quantize(Decimal('0.01'))

        if total_paid >= invoice_total:
            invoice.status = 'paid'
            invoice.paid_date = timezone.now().date()
            messages.success(self.request, f'Invoice {invoice.invoice_number} is now fully paid!')
        else:
            invoice.status = 'partial'
            messages.success(self.request, f'Payment recorded! Remaining: ${(invoice_total - total_paid):.2f}')

        invoice.save()

        return response

    def get_success_url(self):
        return reverse_lazy('invoice_detail', kwargs={'pk': self.object.invoice.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Record Payment'
        context['submit_text'] = 'Process Payment'

        invoice_id = self.kwargs.get('invoice_id')
        if invoice_id:
            invoice = get_object_or_404(Invoice, pk=invoice_id)
            context['invoice'] = invoice

            # Calculate remaining balance
            total_paid = invoice.payments.filter(status='paid').aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0.00')
            remaining_balance = invoice.total_amount - total_paid
            context['remaining_balance'] = remaining_balance.quantize(Decimal('0.01'))

        return context

class PaymentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = 'payments/payment_form.html'

    def test_func(self):
        # Only staff can edit payments
        return self.request.user.is_staff

    def form_valid(self, form):
        messages.success(self.request, f'Payment {form.instance.payment_id} has been updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('payment_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Payment'
        context['submit_text'] = 'Update Payment'
        return context


class PaymentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Payment
    template_name = 'payments/payment_confirm_delete.html'

    def test_func(self):
        # Only staff can delete payments
        return self.request.user.is_staff

    def delete(self, request, *args, **kwargs):
        payment = self.get_object()
        invoice = payment.invoice
        payment_id = payment.payment_id
        response = super().delete(request, *args, **kwargs)

        # Update invoice status after deletion
        total_paid = invoice.payments.filter(status='paid').aggregate(total=Sum('amount'))['total'] or 0

        if total_paid == 0:
            invoice.status = 'pending'
            invoice.paid_date = None
        elif total_paid < invoice.total_amount:
            invoice.status = 'partial'
            invoice.paid_date = None
        else:
            invoice.status = 'paid'
            invoice.paid_date = timezone.now().date()

        invoice.save()

        messages.success(request, f'Payment {payment_id} has been deleted successfully!')
        return response

    def get_success_url(self):
        return reverse_lazy('invoice_detail', kwargs={'pk': self.object.invoice.pk})