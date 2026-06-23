from core.forms import TenantModelForm

from .models import Customer, Supplier


class CustomerForm(TenantModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address',
                  'credit_limit', 'opening_balance', 'is_active']


class SupplierForm(TenantModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'supplier_type', 'phone', 'email', 'address',
                  'opening_balance', 'is_active']
