from django.shortcuts import render
from django.views.generic import TemplateView
from django.db.models import Sum, Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from properties.models import Property
from clients.models import Client
from contracts.models import Contract
from payments.models import Invoice, Payment
from properties.models import PropertyType


class Dashboard(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)
        last_month = today - timedelta(days=30)
        last_week = today - timedelta(days=7)

        # ============ STATS CARDS DATA ============

        # Potential growth (Total Properties Growth)
        last_month_properties = Property.objects.filter(
            created_at__date__gte=last_month,
            created_at__date__lte=today
        ).count()
        total_properties = Property.objects.count()
        potential_growth = (last_month_properties / total_properties * 100) if total_properties > 0 else 0

        # Revenue current (Monthly Revenue)
        monthly_revenue = Payment.objects.filter(
            status='paid',
            payment_date__year=today.year,
            payment_date__month=today.month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Previous month revenue for growth calculation
        prev_month_revenue = Payment.objects.filter(
            status='paid',
            payment_date__year=last_month.year,
            payment_date__month=last_month.month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        revenue_growth = ((monthly_revenue - prev_month_revenue) / prev_month_revenue * 100) if prev_month_revenue > 0 else 0

        # Daily Income (Today's Revenue)
        daily_income = Payment.objects.filter(
            status='paid',
            payment_date=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Yesterday's income for comparison
        yesterday = today - timedelta(days=1)
        yesterday_income = Payment.objects.filter(
            status='paid',
            payment_date=yesterday
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        daily_income_growth = ((daily_income - yesterday_income) / yesterday_income * 100) if yesterday_income > 0 else 0

        # Expense current (Monthly Expenses - Maintenance fees)
        monthly_expenses = Property.objects.filter(
            is_active=True
        ).aggregate(total=Sum('maintenance_fee'))['total'] or Decimal('0')

        # Previous month expenses
        prev_month_expenses = Property.objects.filter(
            created_at__date__lte=last_month
        ).aggregate(total=Sum('maintenance_fee'))['total'] or Decimal('0')

        expense_growth = ((monthly_expenses - prev_month_expenses) / prev_month_expenses * 100) if prev_month_expenses > 0 else 0

        # Update context with stats data
        context['potential_growth_value'] = f"${float(potential_growth):.2f}"
        context['potential_growth_percent'] = f"+{float(potential_growth):.1f}%"

        context['revenue_current_value'] = f"${float(monthly_revenue):.2f}"
        context['revenue_current_percent'] = f"+{float(revenue_growth):.0f}%"

        context['daily_income_value'] = f"${float(daily_income):.2f}"
        context['daily_income_percent'] = f"{'+' if daily_income_growth >= 0 else ''}{float(daily_income_growth):.1f}%"
        context['daily_income_class'] = 'text-success' if daily_income_growth >= 0 else 'text-danger'
        context['daily_income_icon'] = 'arrow-top-right' if daily_income_growth >= 0 else 'arrow-bottom-left'

        context['expense_current_value'] = f"${float(monthly_expenses):.2f}"
        context['expense_current_percent'] = f"+{float(expense_growth):.1f}%"

        # ============ CHART DATA ============

        # Line Chart Data (Last 7 days revenue)
        line_chart_dates = []
        line_chart_values = []

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_total = Payment.objects.filter(
                status='paid',
                payment_date=date
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            line_chart_dates.append(date.strftime('%m/%d'))
            line_chart_values.append(float(daily_total))

        context['line_chart_labels'] = line_chart_dates
        context['line_chart_data'] = line_chart_values

        # Bar Chart Data (Properties by Type)
        property_types = Property.objects.values('property_type').annotate(
            count=Count('id')
        ).order_by('-count')

        bar_chart_labels = []
        bar_chart_data = []

        type_display = {
            'bnb': 'BNB',
            'hotel': 'Hotel',
            'school': 'School',
            'residential': 'Residential',
            'commercial': 'Commercial',
            'land': 'Land',
            'industrial': 'Industrial'
        }

        for ptype in property_types:
            bar_chart_labels.append(type_display.get(ptype['property_type'], ptype['property_type']))
            bar_chart_data.append(ptype['count'])

        context['bar_chart_labels'] = bar_chart_labels
        context['bar_chart_data'] = bar_chart_data

        # ============ TRANSACTION HISTORY ============

        # Total for doughnut chart
        total_payments = Payment.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Payment methods breakdown for doughnut chart
        payment_methods = Payment.objects.filter(status='paid').values('payment_method').annotate(
            total=Sum('amount')
        )

        doughnut_labels = []
        doughnut_data = []

        method_display = {
            'cash': 'Cash',
            'bank_transfer': 'Bank Transfer',
            'credit_card': 'Credit Card',
            'debit_card': 'Debit Card',
            'check': 'Check',
            'online': 'Online'
        }

        for method in payment_methods:
            doughnut_labels.append(method_display.get(method['payment_method'], method['payment_method']))
            doughnut_data.append(float(method['total']))

        context['doughnut_labels'] = doughnut_labels
        context['doughnut_data'] = doughnut_data
        context['total_transactions_value'] = f"${float(total_payments):.0f}"

        # Recent transactions list
        recent_transactions = Payment.objects.filter(status='paid').select_related('client').order_by('-payment_date')[:2]

        transaction_list = []
        for transaction in recent_transactions:
            transaction_list.append({
                'description': f"Payment from {transaction.client.name}",
                'date': transaction.payment_date.strftime('%d %b %Y, %I:%M%p'),
                'amount': f"${float(transaction.amount):.0f}"
            })

        context['recent_transactions'] = transaction_list

        # ============ OPEN PROJECTS (Recent Properties) ============

        recent_properties = Property.objects.filter(is_active=True).select_related('owner').order_by('-created_at')[:5]

        open_projects = []
        for property in recent_properties:
            open_projects.append({
                'title': property.title,
                'description': f"{property.city}, {property.state}",
                'time': property.created_at.strftime('%H:%M'),
                'time_ago': property.created_at.strftime('%I:%M %p'),
                'tasks': property.amenities.count(),
                'issues': property.units.count()
            })

        context['open_projects'] = open_projects

        # ============ BOTTOM STATS CARDS ============

        # Revenue (Total Revenue All Time)
        total_revenue_all = Payment.objects.filter(status='paid').aggregate(total=Sum('amount'))['total'] or Decimal('0')

        # Sales (Active Properties Value)
        active_properties_value = Property.objects.filter(is_active=True, status='available').aggregate(
            total=Sum('price')
        )['total'] or Decimal('0')

        # Purchase (Total Maintenance Fees)
        total_maintenance = Property.objects.filter(is_active=True).aggregate(
            total=Sum('maintenance_fee')
        )['total'] or Decimal('0')

        context['revenue_value'] = f"${float(total_revenue_all):.0f}"
        context['sales_value'] = f"${float(active_properties_value):.0f}"
        context['purchase_value'] = f"${float(total_maintenance):.0f}"

        # Calculate percentages for bottom stats
        last_month_revenue = Payment.objects.filter(
            status='paid',
            payment_date__gte=last_month,
            payment_date__lte=today
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')

        revenue_bottom_growth = ((total_revenue_all - last_month_revenue) / last_month_revenue * 100) if last_month_revenue > 0 else 0

        last_month_sales = Property.objects.filter(
            created_at__date__gte=last_month,
            created_at__date__lte=today
        ).aggregate(total=Sum('price'))['total'] or Decimal('0')

        sales_growth = ((active_properties_value - last_month_sales) / last_month_sales * 100) if last_month_sales > 0 else 0

        last_month_maintenance = Property.objects.filter(
            created_at__date__gte=last_month,
            created_at__date__lte=today
        ).aggregate(total=Sum('maintenance_fee'))['total'] or Decimal('0')

        purchase_growth = ((total_maintenance - last_month_maintenance) / last_month_maintenance * 100) if last_month_maintenance > 0 else -2.1

        context['revenue_bottom_percent'] = f"+{float(revenue_bottom_growth):.2f}%"
        context['sales_bottom_percent'] = f"+{float(sales_growth):.1f}%"
        context['purchase_bottom_percent'] = f"{float(purchase_growth):.1f}%"
        context['purchase_class'] = 'text-success' if purchase_growth >= 0 else 'text-danger'

        return context