from django.contrib import admin
from .models import Contract, ContractSignature, ContractRenewal


class ContractSignatureInline(admin.TabularInline):
    model = ContractSignature
    extra = 0


class ContractRenewalInline(admin.TabularInline):
    model = ContractRenewal
    fk_name = 'original_contract'
    extra = 0


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('contract_number', 'client', 'property', 'contract_type', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'contract_type', 'utilities_included', 'parking_included', 'pets_allowed')
    search_fields = ('contract_number', 'client__name', 'property__title')
    readonly_fields = ('contract_number', 'created_at', 'updated_at')
    inlines = [ContractSignatureInline, ContractRenewalInline]


@admin.register(ContractSignature)
class ContractSignatureAdmin(admin.ModelAdmin):
    list_display = ('contract', 'signer_name', 'is_owner', 'signed_at')
    list_filter = ('is_owner',)
    search_fields = ('signer_name', 'signer_email', 'contract__contract_number')


@admin.register(ContractRenewal)
class ContractRenewalAdmin(admin.ModelAdmin):
    list_display = ('original_contract', 'new_end_date', 'renewal_date', 'approved_by')
