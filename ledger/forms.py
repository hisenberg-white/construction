from django import forms

from core.constants import PaymentMethod
from core.forms import BootstrapFormMixin, DateInput, TenantModelForm

from .models import Payment


class RecordPaymentForm(BootstrapFormMixin, forms.Form):
    """Quick payment recorded against an existing invoice/purchase."""

    amount = forms.DecimalField(max_digits=14, decimal_places=2, min_value=0.01)
    payment_date = forms.DateField(widget=DateInput())
    method = forms.ChoiceField(choices=PaymentMethod.choices, initial=PaymentMethod.CASH)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 2}))


class PaymentForm(TenantModelForm):
    class Meta:
        model = Payment
        fields = ['payment_date', 'depot', 'party_type', 'customer', 'supplier',
                  'employee', 'direction', 'amount', 'method', 'reference_no',
                  'notes', 'reference_image']
        widgets = {'payment_date': DateInput(), 'notes': forms.Textarea(attrs={'rows': 2})}
