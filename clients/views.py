# apps/clients/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db.models import Q, Sum, Count
from .models import Client, ClientDocument, Watchlist, ClientType, Bill, BillCategory, Payment
from .forms import ClientForm, ClientDocumentForm, WatchlistForm, BillForm, TenantAssignForm, TenantPaymentForm
from properties.models import Property
from users.models import Profile
from django.db import models
from django.http import JsonResponse, Http404
from django.utils import timezone
from datetime import timedelta


def user_can_access_client(user, client):
    """
    True if the user is a superuser, created this client record, or the
    client is tied (via a bill/contract/booking) to a property this user
    owns. Used to gate edit/delete access to client records.
    """
    if user.is_superuser:
        return True
    if client.created_by_id == user.id:
        return True
    return Client.objects.filter(pk=client.pk).filter(
        Q(invoices__property__owner=user) |
        Q(contracts__property__owner=user) |
        Q(bookings__property__owner=user)
    ).exists()


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20

    def get_queryset(self):
        queryset = Client.objects.all()

        if not self.request.user.is_superuser:
            owner = self.request.user
            queryset = queryset.filter(
                Q(invoices__property__owner=owner) |
                Q(contracts__property__owner=owner) |
                Q(bookings__property__owner=owner)
            ).distinct()

        # Filter by client type
        client_type = self.request.GET.get('type')
        if client_type:
            queryset = queryset.filter(client_type=client_type)

        # Filter by status
        is_active = self.request.GET.get('is_active')
        if is_active == 'active':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'inactive':
            queryset = queryset.filter(is_active=False)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(city__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        first_day_of_month = today.replace(day=1)

        # Base set of clients this user is allowed to see (unfiltered by search/type)
        base_clients = Client.objects.all()
        if not self.request.user.is_superuser:
            owner = self.request.user
            base_clients = base_clients.filter(
                Q(invoices__property__owner=owner) |
                Q(contracts__property__owner=owner) |
                Q(bookings__property__owner=owner)
            ).distinct()

        total_clients = base_clients.count()
        active_clients = base_clients.filter(is_active=True).count()
        inactive_clients = total_clients - active_clients
        new_clients_month = base_clients.filter(created_at__date__gte=first_day_of_month).count()

        last_month_clients = base_clients.filter(
            created_at__date__gte=today - timedelta(days=30)
        ).count()
        client_growth = (last_month_clients / total_clients * 100) if total_clients > 0 else 0

        # Line chart: new clients per day, last 7 days
        line_chart_labels = []
        line_chart_data = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            count = base_clients.filter(created_at__date=date).count()
            line_chart_labels.append(date.strftime('%m/%d'))
            line_chart_data.append(count)

        # Bar chart: clients by type
        type_display = dict(ClientType.choices)
        type_counts = base_clients.values('client_type').annotate(count=Count('id')).order_by('-count')
        bar_chart_labels = [type_display.get(t['client_type'], t['client_type']) for t in type_counts]
        bar_chart_data = [t['count'] for t in type_counts]

        context.update({
            'client_types': ClientType.choices,
            'total_clients': total_clients,
            'active_clients': active_clients,
            'inactive_clients': inactive_clients,
            'new_clients_month': new_clients_month,
            'client_growth': round(client_growth, 1),
            'line_chart_labels': line_chart_labels,
            'line_chart_data': line_chart_data,
            'bar_chart_labels': bar_chart_labels,
            'bar_chart_data': bar_chart_data,
        })
        return context


class ClientDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'

    def test_func(self):
        return user_can_access_client(self.request.user, self.get_object())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['documents'] = self.object.documents.all()
        context['watchlist'] = self.object.watchlist.all()
        context['contracts'] = self.object.contracts.all()[:10]
        context['payments'] = self.object.payments.all()[:10]
        context['total_spent'] = self.object.payments.filter(status='paid').aggregate(
            total=models.Sum('amount')
        )['total'] or 0
        return context


class ClientCreateView(LoginRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('client_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Client "{form.instance.name}" has been created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Client'
        context['submit_text'] = 'Create Client'
        return context


class ClientUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'clients/client_form.html'
    success_url = reverse_lazy('client_list')

    def test_func(self):
        client = self.get_object()
        return user_can_access_client(self.request.user, client)

    def form_valid(self, form):
        messages.success(self.request, f'Client "{form.instance.name}" has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Client'
        context['submit_text'] = 'Update Client'
        return context


class ClientDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Client
    template_name = 'clients/client_confirm_delete.html'
    success_url = reverse_lazy('client_list')

    def test_func(self):
        client = self.get_object()
        return user_can_access_client(self.request.user, client)

    def delete(self, request, *args, **kwargs):
        client = self.get_object()
        messages.success(request, f'Client "{client.name}" has been deleted successfully!')
        return super().delete(request, *args, **kwargs)


class ClientDocumentCreateView(LoginRequiredMixin, CreateView):
    model = ClientDocument
    form_class = ClientDocumentForm
    template_name = 'clients/document_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.client = get_object_or_404(Client, pk=kwargs['client_pk'])
        if not user_can_access_client(request.user, self.client):
            messages.error(request, "You don't have permission to access this client.")
            return redirect('client_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.client = self.client
        messages.success(self.request, f'Document "{form.instance.title}" has been uploaded successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('client_detail', kwargs={'pk': self.client.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        context['title'] = f'Add Document for {self.client.name}'
        return context


class WatchlistCreateView(LoginRequiredMixin, CreateView):
    model = Watchlist
    form_class = WatchlistForm
    template_name = 'clients/watchlist_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.client = get_object_or_404(Client, pk=kwargs['client_pk'])
        if not user_can_access_client(request.user, self.client):
            messages.error(request, "You don't have permission to access this client.")
            return redirect('client_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.client = self.client
        messages.success(self.request, f'Property added to {self.client.name}\'s watchlist!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('client_detail', kwargs={'pk': self.client.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        context['title'] = f'Add Property to Watchlist for {self.client.name}'
        return context


class WatchlistDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Watchlist
    template_name = 'clients/watchlist_confirm_delete.html'

    def test_func(self):
        return user_can_access_client(self.request.user, self.get_object().client)

    def get_success_url(self):
        return reverse_lazy('client_detail', kwargs={'pk': self.object.client.pk})

    def delete(self, request, *args, **kwargs):
        watchlist_item = self.get_object()
        messages.success(request, f'Property removed from {watchlist_item.client.name}\'s watchlist!')
        return super().delete(request, *args, **kwargs)

class ClientDocumentUploadView(LoginRequiredMixin, CreateView):
    """View for uploading documents for a client"""
    model = ClientDocument
    form_class = ClientDocumentForm
    template_name = 'clients/document_form.html'

    def dispatch(self, request, *args, **kwargs):
        """Get the client before processing the request"""
        self.client = get_object_or_404(Client, pk=kwargs['client_pk'])
        if not user_can_access_client(request.user, self.client):
            messages.error(request, "You don't have permission to access this client.")
            return redirect('client_list')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        """Set the client on the document before saving"""
        form.instance.client = self.client
        messages.success(self.request, f'Document "{form.instance.title}" has been uploaded successfully for {self.client.name}!')
        return super().form_valid(form)

    def get_success_url(self):
        """Redirect back to client detail page after successful upload"""
        return reverse_lazy('client_detail', kwargs={'pk': self.client.pk})

    def get_context_data(self, **kwargs):
        """Add client and title to context"""
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        context['title'] = f'Upload Document for {self.client.name}'
        context['submit_text'] = 'Upload Document'
        return context


class ClientDocumentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for updating client documents"""
    model = ClientDocument
    form_class = ClientDocumentForm
    template_name = 'clients/document_form.html'

    def test_func(self):
        """Only the client's own landlord (or superuser) can edit documents"""
        return user_can_access_client(self.request.user, self.get_object().client)

    def form_valid(self, form):
        messages.success(self.request, f'Document "{form.instance.title}" has been updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('client_detail', kwargs={'pk': self.object.client.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.object.client
        context['title'] = 'Edit Document'
        context['submit_text'] = 'Update Document'
        return context


class ClientDocumentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View for deleting client documents"""
    model = ClientDocument
    template_name = 'clients/document_confirm_delete.html'

    def test_func(self):
        """Only the client's own landlord (or superuser) can delete documents"""
        return user_can_access_client(self.request.user, self.get_object().client)

    def delete(self, request, *args, **kwargs):
        """Delete the document and show success message"""
        document = self.get_object()
        client_name = document.client.name
        document_title = document.title
        messages.success(request, f'Document "{document_title}" has been deleted successfully for {client_name}!')
        return super().delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('client_detail', kwargs={'pk': self.object.client.pk})


class ClientDocumentDownloadView(LoginRequiredMixin, View):
    """View for downloading client documents"""

    def get(self, request, *args, **kwargs):
        document = get_object_or_404(ClientDocument, pk=kwargs['pk'])

        # Check permissions
        if not user_can_access_client(request.user, document.client) and request.user != document.client.user:
            messages.error(request, 'You do not have permission to download this document.')
            return redirect('client_detail', pk=document.client.pk)

        # Serve the file
        from django.http import FileResponse, Http404
        import os

        if document.file and os.path.exists(document.file.path):
            response = FileResponse(open(document.file.path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(document.file.name)}"'
            return response
        else:
            raise Http404("File not found")

# bills
class BillListView(LoginRequiredMixin, ListView):
    """List all bills with filtering"""
    model = Bill
    template_name = 'bill/bill_list.html'
    context_object_name = 'bills'
    paginate_by = 10

    def get_queryset(self):
        queryset = Bill.objects.filter(is_active=True).select_related('property', 'category', 'user')

        # Filter by search
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(description__icontains=search) |
                Q(reference_number__icontains=search) |
                Q(property__title__icontains=search)
            )

        # Non-superusers only see bills for properties they own
        if not self.request.user.is_superuser:
            user_properties = Property.objects.filter(owner=self.request.user)
            queryset = queryset.filter(property__in=user_properties)

        # Filter by property
        property_id = self.request.GET.get('property', '')
        if property_id:
            queryset = queryset.filter(property_id=property_id)

        # Filter by bill type
        bill_type = self.request.GET.get('bill_type', '')
        if bill_type:
            queryset = queryset.filter(bill_type=bill_type)

        # Filter by status
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by date range
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            queryset = queryset.filter(due_date__gte=date_from)

        date_to = self.request.GET.get('date_to', '')
        if date_to:
            queryset = queryset.filter(due_date__lte=date_to)

        # Filter by amount range
        min_amount = self.request.GET.get('min_amount', '')
        if min_amount:
            try:
                queryset = queryset.filter(amount__gte=float(min_amount))
            except (ValueError, TypeError):
                pass

        max_amount = self.request.GET.get('max_amount', '')
        if max_amount:
            try:
                queryset = queryset.filter(amount__lte=float(max_amount))
            except (ValueError, TypeError):
                pass

        # Sort - whitelist fields so an arbitrary ?sort= value can't raise
        # a FieldError (500 error) or be used to probe the schema
        allowed_sort_fields = {
            'due_date', '-due_date', 'amount', '-amount',
            'created_at', '-created_at', 'status', '-status',
        }
        sort_by = self.request.GET.get('sort', '-due_date')
        if sort_by not in allowed_sort_fields:
            sort_by = '-due_date'
        queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get all bills for stats
        bills = self.get_queryset()

        # Statistics
        context['total_bills'] = bills.count()
        context['paid_bills'] = bills.filter(status='paid').count()
        context['pending_bills'] = bills.filter(status='pending').count()
        context['overdue_bills'] = bills.filter(status='overdue').count()
        context['total_amount'] = bills.aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_paid'] = bills.filter(status='paid').aggregate(Sum('amount'))['amount__sum'] or 0
        context['total_due'] = bills.filter(status__in=['pending', 'overdue']).aggregate(Sum('amount'))['amount__sum'] or 0

        # For filters dropdown
        context['properties'] = Property.objects.filter(is_active=True) if self.request.user.is_superuser else Property.objects.filter(is_active=True, owner=self.request.user)
        context['bill_types'] = Bill.BILL_TYPES
        context['status_choices'] = Bill.BILL_STATUS
        context['categories'] = BillCategory.objects.filter(is_active=True)

        # Current filter values
        context['current_search'] = self.request.GET.get('search', '')
        context['current_property'] = self.request.GET.get('property', '')
        context['current_bill_type'] = self.request.GET.get('bill_type', '')
        context['current_status'] = self.request.GET.get('status', '')
        context['current_date_from'] = self.request.GET.get('date_from', '')
        context['current_date_to'] = self.request.GET.get('date_to', '')
        context['current_min_amount'] = self.request.GET.get('min_amount', '')
        context['current_max_amount'] = self.request.GET.get('max_amount', '')
        context['current_sort'] = self.request.GET.get('sort', '-due_date')

        return context


class BillCreateView(LoginRequiredMixin, CreateView):
    """Create a new bill"""
    model = Bill
    form_class = BillForm
    template_name = 'bill/bill_form.html'
    success_url = reverse_lazy('bill_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f'Bill "{form.instance.description}" has been created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add New Bill'
        context['submit_text'] = 'Create Bill'
        context['is_edit'] = False
        return context


class BillUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update an existing bill"""
    model = Bill
    form_class = BillForm
    template_name = 'bill/bill_form.html'
    success_url = reverse_lazy('bill_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def test_func(self):
        bill = self.get_object()
        return self.request.user.is_superuser or self.request.user == bill.property.owner

    def form_valid(self, form):
        messages.success(self.request, f'Bill "{form.instance.description}" has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Bill'
        context['submit_text'] = 'Update Bill'
        context['is_edit'] = True
        return context


class BillDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a bill"""
    model = Bill
    success_url = reverse_lazy('bill_list')

    def test_func(self):
        bill = self.get_object()
        return self.request.user.is_superuser or self.request.user == bill.property.owner

    def delete(self, request, *args, **kwargs):
        bill = self.get_object()
        messages.success(request, f'Bill "{bill.description}" has been deleted successfully!')
        return super().delete(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # Redirect GET requests to list view
        return redirect('bill_list')


class BillMarkPaidView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Mark a bill as paid"""
    model = Bill
    fields = []
    template_name = 'bill/bill_mark_paid.html'
    success_url = reverse_lazy('bill_list')

    def test_func(self):
        bill = self.get_object()
        return self.request.user.is_superuser or self.request.user == bill.property.owner

    def form_valid(self, form):
        bill = self.get_object()
        bill.mark_as_paid()
        messages.success(self.request, f'Bill "{bill.description}" has been marked as paid!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Mark Bill as Paid'
        return context

# ─────────────────────────────────────────────────────────────────────────
# Tenant management — landlords add/remove tenants on their properties;
# tenants view and pay their own rent from the front end.
#
# A "tenant" here is simply a User whose Profile.current_property points
# at one of the landlord's properties (see users/models.py Profile). Bills
# are clients.Bill rows scoped to that property/user.
# ─────────────────────────────────────────────────────────────────────────

def _owned_property_ids(user):
    if user.is_superuser:
        return Property.objects.filter(is_active=True).values_list('id', flat=True)
    return Property.objects.filter(owner=user, is_active=True).values_list('id', flat=True)


class TenantListView(LoginRequiredMixin, ListView):
    """Landlord roster: every tenant currently living in one of my
    properties, with this month's rent status so it's obvious at a glance
    who has and hasn't paid."""
    model = Profile
    template_name = 'clients/tenant_list.html'
    context_object_name = 'tenants'
    paginate_by = 20

    def get_queryset(self):
        return Profile.objects.filter(
            current_property_id__in=_owned_property_ids(self.request.user)
        ).select_related('user', 'current_property').order_by('current_property__title', 'user__first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        month_start = today.replace(day=1)

        rows = []
        for profile in context['tenants']:
            rent_bill = Bill.objects.filter(
                property=profile.current_property,
                user=profile.user,
                bill_type='rent',
                due_date__gte=month_start,
            ).order_by('due_date').first()
            rows.append({
                'profile': profile,
                'rent_bill': rent_bill,
            })
        context['tenant_rows'] = rows
        context['total_tenants'] = len(rows)
        context['paid_this_month'] = sum(1 for r in rows if r['rent_bill'] and r['rent_bill'].status == 'paid')
        context['unpaid_this_month'] = context['total_tenants'] - context['paid_this_month']
        context['properties'] = Property.objects.filter(id__in=_owned_property_ids(self.request.user))
        return context


class TenantAssignView(LoginRequiredMixin, FormView):
    """Landlord adds an existing 2Hame user as a tenant on one of their
    properties, wiring up Profile.current_property and (optionally) the
    first rent bill in one step."""
    template_name = 'clients/tenant_assign_form.html'
    form_class = TenantAssignForm
    success_url = reverse_lazy('tenant_list')

    def get_initial_property(self):
        property_pk = self.kwargs.get('property_pk')
        if not property_pk:
            return None
        return get_object_or_404(Property, pk=property_pk, id__in=_owned_property_ids(self.request.user))

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['preset_property'] = self.get_initial_property()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Tenant'
        context['preset_property'] = self.get_initial_property()
        return context

    def form_valid(self, form):
        property_obj = form.cleaned_data['property']
        tenant_user = form.cleaned_data['tenant_user']
        monthly_rent = form.cleaned_data['monthly_rent']
        moved_in_date = form.cleaned_data['moved_in_date']

        profile, _ = Profile.objects.get_or_create(user=tenant_user)
        previous_property = profile.current_property
        profile.move_to_property(property_obj, moved_in_date=moved_in_date)

        if form.cleaned_data.get('generate_first_bill'):
            Bill.objects.get_or_create(
                property=property_obj,
                user=tenant_user,
                bill_type='rent',
                due_date=moved_in_date,
                defaults={
                    'description': f'Rent \u2013 {property_obj.title}',
                    'amount': monthly_rent,
                    'status': 'pending',
                    'is_recurring': True,
                    'recurrence_interval': 'monthly',
                },
            )

        tenant_name = tenant_user.get_full_name() or tenant_user.username
        if previous_property and previous_property != property_obj:
            messages.success(
                self.request,
                f'{tenant_name} has been moved from {previous_property.title} to {property_obj.title}.'
            )
        else:
            messages.success(self.request, f'{tenant_name} has been added as a tenant at {property_obj.title}.')

        return super().form_valid(form)


class TenantRemoveView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Landlord marks a tenant as moved out - clears Profile.current_property.
    Existing bills/payments are left untouched for the record."""

    def test_func(self):
        profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
        if not profile.current_property:
            return False
        return self.request.user.is_superuser or profile.current_property.owner_id == self.request.user.id

    def post(self, request, *args, **kwargs):
        profile = get_object_or_404(Profile, pk=self.kwargs['pk'])
        tenant_name = profile.user.get_full_name() or profile.user.username
        property_title = profile.current_property.title if profile.current_property else ''
        profile.leave_current_property()
        messages.success(request, f'{tenant_name} has been marked as moved out of {property_title}.')
        return redirect('tenant_list')

    def get(self, request, *args, **kwargs):
        return redirect('tenant_list')


class TenantBillPayView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Tenant-facing: pay a bill of their own and mark it paid. This is the
    front-end counterpart to the landlord-only BillMarkPaidView above."""
    template_name = 'bill/tenant_pay_bill.html'

    def get_bill(self):
        return get_object_or_404(Bill, pk=self.kwargs['pk'])

    def test_func(self):
        bill = self.get_bill()
        user = self.request.user
        profile = getattr(user, 'profile', None)
        is_billed_tenant = bill.user_id == user.id
        is_resident = profile and profile.current_property_id == bill.property_id
        return is_billed_tenant or is_resident

    def get(self, request, *args, **kwargs):
        bill = self.get_bill()
        if bill.status == 'paid':
            messages.info(request, 'This bill is already marked as paid.')
            return redirect('my_profile')
        form = TenantPaymentForm()
        return render(request, self.template_name, {'bill': bill, 'form': form})

    def post(self, request, *args, **kwargs):
        bill = self.get_bill()
        if bill.status == 'paid':
            messages.info(request, 'This bill is already marked as paid.')
            return redirect('my_profile')

        form = TenantPaymentForm(request.POST)
        if form.is_valid():
            reference = form.cleaned_data.get('transaction_id', '')
            payment = Payment.objects.create(
                user=request.user,
                bill=bill,
                amount=bill.amount,
                payment_method=form.cleaned_data['payment_method'],
                payment_status='pending',
                transaction_id=reference,
            )
            payment.mark_completed(transaction_id=reference)  # also marks the bill paid
            messages.success(request, f'Payment recorded \u2013 "{bill.description}" is now marked as paid.')
            return redirect('my_profile')

        return render(request, self.template_name, {'bill': bill, 'form': form})
