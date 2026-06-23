from django import forms

from core.forms import BootstrapFormMixin, TenantModelForm

from .models import (
    MaterialItem,
    ServiceItem,
    StockLedger,
    Vehicle,
    VehicleCapacityRule,
    VehicleType,
)


class MaterialItemForm(TenantModelForm):
    class Meta:
        model = MaterialItem
        fields = ['name', 'category', 'base_unit', 'default_purchase_rate',
                  'default_sale_rate', 'stock_enabled', 'is_active']


class ServiceItemForm(TenantModelForm):
    class Meta:
        model = ServiceItem
        fields = ['name', 'unit_type', 'default_rate', 'is_active']


class VehicleTypeForm(TenantModelForm):
    class Meta:
        model = VehicleType
        fields = ['name', 'default_capacity', 'capacity_unit', 'is_active']


class VehicleForm(TenantModelForm):
    class Meta:
        model = Vehicle
        fields = ['vehicle_type', 'name', 'is_active']


class VehicleCapacityRuleForm(TenantModelForm):
    class Meta:
        model = VehicleCapacityRule
        fields = ['material', 'from_vehicle_type', 'to_vehicle_type', 'conversion_factor']


class StockAdjustmentForm(BootstrapFormMixin, forms.Form):
    """Manual stock adjustment posted through StockService (SRS FR-09)."""

    DIRECTIONS = [
        (StockLedger.TransactionType.ADJUST_IN, 'Adjustment In (+)'),
        (StockLedger.TransactionType.ADJUST_OUT, 'Adjustment Out (−)'),
        (StockLedger.TransactionType.DAMAGE, 'Damage / Loss (−)'),
        (StockLedger.TransactionType.TRANSFER_IN, 'Transfer In (+)'),
        (StockLedger.TransactionType.TRANSFER_OUT, 'Transfer Out (−)'),
    ]

    depot = forms.ModelChoiceField(queryset=None)
    material = forms.ModelChoiceField(queryset=None)
    transaction_type = forms.ChoiceField(choices=DIRECTIONS)
    qty = forms.DecimalField(max_digits=14, decimal_places=3, min_value=0)
    note = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, tenant=None, **kwargs):
        from tenants.models import DepotLocation
        super().__init__(*args, **kwargs)
        self.fields['depot'].queryset = DepotLocation.objects.filter(tenant=tenant)
        self.fields['material'].queryset = MaterialItem.objects.filter(tenant=tenant)
