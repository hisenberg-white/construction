from django import forms

from core.forms import BootstrapFormMixin, DateInput

from .models import SaaSPlan, Subscription


class SaaSPlanForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = SaaSPlan
        fields = ['name', 'billing_cycle', 'base_price', 'per_entry_price',
                  'user_limit', 'depot_limit', 'entry_limit', 'storage_limit_mb',
                  'is_active']


class SubscriptionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['tenant', 'plan', 'start_date', 'end_date', 'grace_days',
                  'renewal_date', 'custom_per_entry_price', 'is_current']
        widgets = {
            'start_date': DateInput(),
            'end_date': DateInput(),
            'renewal_date': DateInput(),
        }
