from django.contrib import admin

from .models import DeliveryLog, SaleInvoice, SaleInvoiceLine


class SaleInvoiceLineInline(admin.TabularInline):
    model = SaleInvoiceLine
    extra = 0


@admin.register(SaleInvoice)
class SaleInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_no', 'tenant', 'depot', 'customer',
                    'invoice_date', 'total', 'due', 'payment_status', 'status')
    list_filter = ('tenant', 'depot', 'payment_status', 'status')
    search_fields = ('invoice_no', 'customer__name')
    date_hierarchy = 'invoice_date'
    inlines = [SaleInvoiceLineInline]


@admin.register(DeliveryLog)
class DeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'method', 'recipient', 'delivery_status', 'created_at')
    list_filter = ('tenant', 'method', 'delivery_status')
