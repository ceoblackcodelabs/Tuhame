# apps/report/views.py
from django.views.generic import ListView, DetailView, CreateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
import json
from .models import Report, ReportStatus, ReportType
from .forms import GenerateReportForm, DailyReportForm
from properties.models import Property
from clients.models import Client
from contracts.models import Contract
from payments.models import Invoice, Payment


class ReportListView(LoginRequiredMixin, ListView):
    """View to list all generated reports"""
    model = Report
    template_name = 'report/report_list.html'
    context_object_name = 'reports'
    paginate_by = 15

    def get_queryset(self):
        queryset = Report.objects.all()

        # Filter by report type
        report_type = self.request.GET.get('type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)

        # Filter by date range
        date_from = self.request.GET.get('date_from')
        if date_from:
            queryset = queryset.filter(generated_at__date__gte=date_from)

        date_to = self.request.GET.get('date_to')
        if date_to:
            queryset = queryset.filter(generated_at__date__lte=date_to)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(report_id__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_types'] = ReportType.choices
        context['total_reports'] = Report.objects.count()
        context['recent_reports'] = Report.objects.filter(
            generated_at__date__gte=timezone.now().date() - timezone.timedelta(days=7)
        ).count()
        return context


class ReportDetailView(LoginRequiredMixin, DetailView):
    """View to display a specific report"""
    model = Report
    template_name = 'report/report_detail.html'
    context_object_name = 'report'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Update last accessed time
        obj.last_accessed = timezone.now()
        obj.save(update_fields=['last_accessed'])
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_data = self.object.report_data

        # Prepare chart data if available
        if report_data:
            context['chart_data'] = json.dumps(report_data.get('charts', {}))
            context['property_types_data'] = json.dumps(report_data.get('property_types', []))
            context['payment_methods_data'] = json.dumps(report_data.get('payment_methods', []))

        return context


class ReportGenerateView(LoginRequiredMixin, FormView):
    """View to generate a new report"""
    template_name = 'report/report_generate.html'
    form_class = GenerateReportForm
    success_url = reverse_lazy('report_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Generate New Report'
        context['submit_text'] = 'Generate Report'
        return context

    def form_valid(self, form):
        # Create report instance
        report = Report(
            report_type=form.cleaned_data['report_type'],
            title=form.cleaned_data['title'],
            description=form.cleaned_data['description'],
            start_date=form.cleaned_data['start_date'],
            end_date=form.cleaned_data['end_date'],
            generated_by=self.request.user,
            status=ReportStatus.GENERATING,
            parameters={
                'include_charts': form.cleaned_data.get('include_charts', True),
                'include_details': form.cleaned_data.get('include_details', True),
            }
        )
        report.save()

        try:
            # Generate report data
            self.generate_report_data(report)
            report.status = ReportStatus.COMPLETED
            report.save()
            messages.success(self.request, f'Report "{report.title}" has been generated successfully!')
            return redirect('report_detail', pk=report.pk)
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.save()
            messages.error(self.request, f'Error generating report: {str(e)}')
            return self.form_invalid(form)

    def generate_report_data(self, report):
        """Generate all report statistics"""
        start_date = report.start_date
        end_date = report.end_date

        # Property statistics
        total_properties = Property.objects.filter(
            is_active=True,
            created_at__date__lte=end_date
        ).count()

        new_properties = Property.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).count()

        property_by_type = Property.objects.filter(
            created_at__date__lte=end_date
        ).values('property_type').annotate(
            count=Count('id')
        )

        # Convert to list for JSON
        property_types_list = []
        for item in property_by_type:
            property_types_list.append({
                'property_type': item['property_type'],
                'count': item['count']
            })

        # Client statistics
        total_clients = Client.objects.filter(
            is_active=True,
            created_at__date__lte=end_date
        ).count()

        new_clients = Client.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).count()

        client_by_type = Client.objects.filter(
            created_at__date__lte=end_date
        ).values('client_type').annotate(
            count=Count('id')
        )

        client_types_list = []
        for item in client_by_type:
            client_types_list.append({
                'client_type': item['client_type'],
                'count': item['count']
            })

        # Contract statistics
        total_contracts = Contract.objects.filter(
            start_date__lte=end_date
        ).count()

        active_contracts = Contract.objects.filter(
            status='active',
            start_date__lte=end_date,
            end_date__gte=start_date
        ).count()

        expiring_contracts = Contract.objects.filter(
            status='active',
            end_date__gte=start_date,
            end_date__lte=end_date + timezone.timedelta(days=30)
        ).count()

        # Financial statistics
        payments = Payment.objects.filter(
            status='paid',
            payment_date__gte=start_date,
            payment_date__lte=end_date
        )

        total_revenue = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        payment_by_method = payments.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        )

        payment_methods_list = []
        for item in payment_by_method:
            payment_methods_list.append({
                'payment_method': item['payment_method'],
                'count': item['count'],
                'total': float(item['total']) if item['total'] else 0
            })

        # Invoice statistics
        invoices = Invoice.objects.filter(
            issue_date__gte=start_date,
            issue_date__lte=end_date
        )

        total_invoices = invoices.count()
        paid_invoices = invoices.filter(status='paid').count()
        pending_invoices = invoices.filter(status='pending').aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')

        overdue_invoices = Invoice.objects.filter(
            status='pending',
            due_date__lt=timezone.now().date(),
            due_date__gte=start_date
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

        # Daily breakdown (for daily report)
        daily_data = []
        if report.report_type == ReportType.DAILY:
            current_date = start_date
            while current_date <= end_date:
                day_payments = Payment.objects.filter(
                    status='paid',
                    payment_date=current_date
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

                daily_data.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'revenue': float(day_payments),
                    'transactions': Payment.objects.filter(payment_date=current_date).count()
                })
                current_date += timezone.timedelta(days=1)

        # Update report statistics
        report.total_properties = total_properties
        report.total_clients = total_clients
        report.total_contracts = total_contracts
        report.total_revenue = total_revenue
        report.total_payments = total_revenue
        report.pending_invoices = pending_invoices
        report.overdue_invoices = overdue_invoices

        # Store detailed data in JSON field
        report.report_data = {
            'summary': {
                'total_properties': total_properties,
                'new_properties': new_properties,
                'total_clients': total_clients,
                'new_clients': new_clients,
                'total_contracts': total_contracts,
                'active_contracts': active_contracts,
                'expiring_contracts': expiring_contracts,
                'total_revenue': float(total_revenue),
                'total_invoices': total_invoices,
                'paid_invoices': paid_invoices,
                'pending_invoices': float(pending_invoices),
                'overdue_invoices': float(overdue_invoices),
            },
            'property_types': property_types_list,
            'client_types': client_types_list,
            'payment_methods': payment_methods_list,
            'daily_breakdown': daily_data,
            'charts': {
                'revenue_trend': daily_data,
                'property_distribution': property_types_list,
                'payment_distribution': payment_methods_list,
            }
        }

        report.save()


class DailyReportView(LoginRequiredMixin, FormView):
    """Special view for generating daily report for a specific date"""
    template_name = 'report/daily_report_form.html'
    form_class = DailyReportForm
    success_url = reverse_lazy('report_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Generate Daily Report'
        context['submit_text'] = 'Generate Daily Report'
        return context

    def form_valid(self, form):
        report_date = form.cleaned_data['report_date']

        # Create report title
        title = f"Daily Report - {report_date.strftime('%B %d, %Y')}"

        # Create report instance
        report = Report(
            report_type=ReportType.DAILY,
            title=title,
            description=f"Daily report for {report_date.strftime('%B %d, %Y')}",
            start_date=report_date,
            end_date=report_date,
            generated_for_date=report_date,
            generated_by=self.request.user,
            status=ReportStatus.GENERATING
        )
        report.save()

        try:
            self.generate_daily_report_data(report, report_date)
            report.status = ReportStatus.COMPLETED
            report.save()
            messages.success(self.request, f'Daily report for {report_date.strftime("%B %d, %Y")} has been generated!')
            return redirect('report_detail', pk=report.pk)
        except Exception as e:
            report.status = ReportStatus.FAILED
            report.save()
            messages.error(self.request, f'Error generating daily report: {str(e)}')
            return self.form_invalid(form)

    def generate_daily_report_data(self, report, report_date):
        """Generate daily report data for a specific date"""

        # Daily property statistics
        new_properties = Property.objects.filter(
            created_at__date=report_date
        ).count()

        # Daily client statistics
        new_clients = Client.objects.filter(
            created_at__date=report_date
        ).count()

        # Daily financial statistics
        daily_payments = Payment.objects.filter(
            status='paid',
            payment_date=report_date
        )
        daily_revenue = daily_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Daily transactions
        daily_invoices = Invoice.objects.filter(
            issue_date=report_date
        ).count()

        # Payment breakdown by method
        payment_breakdown = daily_payments.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('amount')
        )

        # Convert payment breakdown for JSON serialization
        payment_breakdown_list = []
        for item in payment_breakdown:
            payment_breakdown_list.append({
                'payment_method': item['payment_method'],
                'count': item['count'],
                'total': float(item['total']) if item['total'] else 0
            })

        # Top properties (by revenue)
        top_properties = daily_payments.values(
            'invoice__property__title',
            'invoice__property__city'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total')[:5]

        top_properties_list = []
        for item in top_properties:
            top_properties_list.append({
                'name': item['invoice__property__title'] or 'Unknown',
                'city': item['invoice__property__city'] or 'Unknown',
                'revenue': float(item['total']) if item['total'] else 0
            })

        # Update report statistics
        report.total_properties = Property.objects.filter(is_active=True).count()
        report.total_clients = Client.objects.filter(is_active=True).count()
        report.total_revenue = daily_revenue
        report.total_payments = daily_revenue

        # Store detailed daily data
        report.report_data = {
            'report_date': report_date.strftime('%Y-%m-%d'),
            'summary': {
                'new_properties': new_properties,
                'new_clients': new_clients,
                'daily_revenue': float(daily_revenue),
                'daily_transactions': daily_payments.count(),
                'daily_invoices': daily_invoices,
            },
            'payment_breakdown': payment_breakdown_list,
            'top_properties': top_properties_list,
            'hourly_breakdown': self.get_hourly_breakdown(report_date),
        }

        report.save()

    def get_hourly_breakdown(self, report_date):
        """Get hourly payment breakdown for the day"""
        hourly_data = []
        for hour in range(24):
            payments = Payment.objects.filter(
                status='paid',
                payment_date=report_date,
                created_at__hour=hour
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

            hourly_data.append({
                'hour': hour,
                'amount': float(payments)
            })
        return hourly_data


class ReportDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View to delete a report"""
    model = Report
    template_name = 'report/report_confirm_delete.html'
    success_url = reverse_lazy('report_list')

    def test_func(self):
        report = self.get_object()
        return self.request.user.is_staff or self.request.user == report.generated_by

    def delete(self, request, *args, **kwargs):
        report = self.get_object()
        messages.success(request, f'Report "{report.title}" has been deleted successfully!')
        return super().delete(request, *args, **kwargs)