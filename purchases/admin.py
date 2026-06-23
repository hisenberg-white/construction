from django.contrib import admin

from .models import Purchase, PurchaseExpense, Trip


class PurchaseExpenseInline(admin.TabularInline):
    model = PurchaseExpense
    extra = 0


@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    inlines = [PurchaseExpenseInline]
    list_display = ('id', 'tenant', 'depot', 'supplier', 'material',
                    'qty', 'total_cost', 'payment_status', 'status')
    list_filter = ('tenant', 'depot', 'payment_status', 'status')
    search_fields = ('reference_no', 'supplier__name', 'material__name')
    date_hierarchy = 'purchase_date'


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('id', 'tenant', 'depot', 'material', 'total_qty',
                    'sold_qty', 'excess_qty', 'trip_status', 'status')
    list_filter = ('tenant', 'depot', 'trip_status', 'status')
