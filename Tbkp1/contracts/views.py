# apps/contracts/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone

from .models import Contract, ContractStatus, ContractType
from .forms import ContractForm


class ContractListView(LoginRequiredMixin, ListView):
    """List all contracts with filtering"""
    model = Contract
    template_name = 'contracts/contract_list.html'
    context_object_name = 'contracts'
    paginate_by = 20

    def get_queryset(self):
        queryset = Contract.objects.all().select_related('property', 'client', 'owner')

        if not self.request.user.is_superuser:
            queryset = queryset.filter(property__owner=self.request.user)

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        contract_type = self.request.GET.get('contract_type')
        if contract_type:
            queryset = queryset.filter(contract_type=contract_type)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(contract_number__icontains=search) |
                Q(client__name__icontains=search) |
                Q(property__title__icontains=search)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ContractStatus.choices
        context['type_choices'] = ContractType.choices

        own_contracts = Contract.objects.all() if self.request.user.is_superuser else Contract.objects.filter(property__owner=self.request.user)

        context['total_contracts'] = own_contracts.count()
        context['active_contracts'] = own_contracts.filter(status=ContractStatus.ACTIVE).count()
        context['pending_contracts'] = own_contracts.filter(status=ContractStatus.PENDING).count()
        context['expiring_soon'] = own_contracts.filter(
            status=ContractStatus.ACTIVE,
            end_date__gte=timezone.now().date(),
            end_date__lte=timezone.now().date() + timezone.timedelta(days=30)
        ).count()

        context['current_status'] = self.request.GET.get('status', '')
        context['current_type'] = self.request.GET.get('contract_type', '')
        context['current_search'] = self.request.GET.get('search', '')

        return context


class ContractDetailView(LoginRequiredMixin, DetailView):
    model = Contract
    template_name = 'contracts/contract_detail.html'
    context_object_name = 'contract'

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_superuser:
            queryset = queryset.filter(property__owner=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['signatures'] = self.object.signatures.all()
        context['renewals'] = self.object.renewals.all()
        return context


class ContractCreateView(LoginRequiredMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_form.html'
    success_url = reverse_lazy('contract_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # A non-superuser can only create contracts for properties they own
        if not self.request.user.is_superuser and form.instance.property.owner != self.request.user:
            messages.error(self.request, "You can only create contracts for properties you own.")
            return self.form_invalid(form)
        messages.success(self.request, f'Contract for {form.instance.client} has been created successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Contract'
        context['submit_text'] = 'Create Contract'
        return context


class ContractUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = 'contracts/contract_form.html'
    success_url = reverse_lazy('contract_list')

    def test_func(self):
        contract = self.get_object()
        owns_it = self.request.user.is_superuser or contract.property.owner == self.request.user
        # Only staff can edit contracts, and only while they're not yet completed/terminated
        return owns_it and contract.status not in [
            ContractStatus.COMPLETED, ContractStatus.TERMINATED
        ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, f'Contract {form.instance.contract_number} has been updated successfully!')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Contract'
        context['submit_text'] = 'Update Contract'
        return context


class ContractDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Contract
    template_name = 'contracts/contract_confirm_delete.html'
    success_url = reverse_lazy('contract_list')

    def test_func(self):
        contract = self.get_object()
        return self.request.user.is_superuser or contract.property.owner == self.request.user

    def delete(self, request, *args, **kwargs):
        contract = self.get_object()
        contract_number = contract.contract_number
        messages.success(request, f'Contract {contract_number} has been deleted successfully!')
        return super().delete(request, *args, **kwargs)


class ActivateContractView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Move a contract from draft/pending to active"""

    def test_func(self):
        contract = get_object_or_404(Contract, pk=self.kwargs['pk'])
        return self.request.user.is_superuser or contract.property.owner == self.request.user

    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        if contract.status in [ContractStatus.DRAFT, ContractStatus.PENDING]:
            contract.status = ContractStatus.ACTIVE
            if not contract.signed_date:
                contract.signed_date = timezone.now().date()
            contract.save()
            messages.success(request, f'Contract {contract.contract_number} is now active.')
        else:
            messages.warning(request, 'This contract cannot be activated from its current status.')
        return redirect('contract_detail', pk=pk)


class TerminateContractView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Terminate an active contract"""

    def test_func(self):
        contract = get_object_or_404(Contract, pk=self.kwargs['pk'])
        return self.request.user.is_superuser or contract.property.owner == self.request.user

    def post(self, request, pk):
        contract = get_object_or_404(Contract, pk=pk)
        if contract.status == ContractStatus.ACTIVE:
            contract.status = ContractStatus.TERMINATED
            contract.termination_date = timezone.now().date()
            contract.save()
            messages.success(request, f'Contract {contract.contract_number} has been terminated.')
        else:
            messages.warning(request, 'Only active contracts can be terminated.')
        return redirect('contract_detail', pk=pk)
