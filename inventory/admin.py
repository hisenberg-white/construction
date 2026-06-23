from django.contrib import admin

from .models import (
    MaterialItem,
    ServiceItem,
    StockLedger,
    Vehicle,
    VehicleCapacityRule,
    VehicleType,
)


@admin.register(MaterialItem)
class MaterialItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'base_unit', 'default_sale_rate',
                    'stock_enabled', 'is_active')
    list_filter = ('tenant', 'stock_enabled', 'is_active')
    search_fields = ('name', 'category')


@admin.register(ServiceItem)
class ServiceItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'unit_type', 'default_rate', 'is_active')
    list_filter = ('tenant', 'unit_type', 'is_active')
    search_fields = ('name',)


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'default_capacity', 'capacity_unit', 'is_active')
    list_filter = ('tenant', 'is_active')
    search_fields = ('name',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'vehicle_type', 'is_active')
    list_filter = ('tenant', 'vehicle_type', 'is_active')
    search_fields = ('name',)


@admin.register(VehicleCapacityRule)
class VehicleCapacityRuleAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'material', 'from_vehicle_type', 'to_vehicle_type',
                    'conversion_factor')
    list_filter = ('tenant',)


@admin.register(StockLedger)
class StockLedgerAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'tenant', 'depot', 'material',
                    'transaction_type', 'qty_in', 'qty_out', 'balance_after')
    list_filter = ('tenant', 'depot', 'transaction_type')
    search_fields = ('material__name',)
    date_hierarchy = 'created_at'
