from django.contrib import admin

from .models import Customer, Supplier


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'phone', 'credit_limit',
                    'opening_balance', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name', 'phone', 'email')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'supplier_type', 'phone',
                    'opening_balance', 'is_active')
    list_filter = ('tenant', 'supplier_type', 'is_active')
    search_fields = ('name', 'phone', 'email')
