# apps/clients/views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Client, ClientDocument, Watchlist, ClientType
from .forms import ClientForm, ClientDocumentForm, WatchlistForm
from properties.models import Property
from django.db import models


class ClientListView(LoginRequiredMixin, ListView):
    model = Client
    template_name = 'clients/client_list.html'
    context_object_name = 'clients'
    paginate_by = 20

    def get_queryset(self):
        queryset = Client.objects.all()

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
        context['client_types'] = ClientType.choices
        context['total_clients'] = Client.objects.count()
        context['active_clients'] = Client.objects.filter(is_active=True).count()
        return context


class ClientDetailView(LoginRequiredMixin, DetailView):
    model = Client
    template_name = 'clients/client_detail.html'
    context_object_name = 'client'

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
        # Allow staff or the user who created the client to edit
        client = self.get_object()
        return self.request.user.is_staff or self.request.user == client.created_by

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
        # Allow staff or the user who created the client to delete
        client = self.get_object()
        return self.request.user.is_staff or self.request.user == client.created_by

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
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.client = self.client
        messages.success(self.request, f'Document "{form.instance.title}" has been uploaded successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('detail', kwargs={'pk': self.client.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.client
        context['title'] = f'Add Document for {self.client.name}'
        return context


class ClientDocumentDeleteView(LoginRequiredMixin, DeleteView):
    model = ClientDocument
    template_name = 'clients/document_confirm_delete.html'

    def get_success_url(self):
        return reverse_lazy('client_detail', kwargs={'pk': self.object.client.pk})

    def delete(self, request, *args, **kwargs):
        document = self.get_object()
        client_name = document.client.name
        messages.success(request, f'Document "{document.title}" has been deleted successfully!')
        return super().delete(request, *args, **kwargs)


class WatchlistCreateView(LoginRequiredMixin, CreateView):
    model = Watchlist
    form_class = WatchlistForm
    template_name = 'clients/watchlist_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.client = get_object_or_404(Client, pk=kwargs['client_pk'])
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


class WatchlistDeleteView(LoginRequiredMixin, DeleteView):
    model = Watchlist
    template_name = 'clients/watchlist_confirm_delete.html'

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
        """Only staff can edit documents"""
        return self.request.user.is_staff

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
        """Only staff can delete documents"""
        return self.request.user.is_staff

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
        if not request.user.is_staff and request.user != document.client.user:
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