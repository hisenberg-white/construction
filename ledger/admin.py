from django.contrib import admin

from .models import LedgerEntry, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'party_type', 'direction', 'amount',
                    'method', 'payment_date', 'status')
    list_filter = ('tenant', 'party_type', 'direction', 'method', 'status')
    search_fields = ('reference_no',)
    date_hierarchy = 'payment_date'


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_date', 'tenant', 'account_type', 'account_id',
                    'debit', 'credit', 'balance_after')
    list_filter = ('tenant', 'account_type')
    date_hierarchy = 'entry_date'
