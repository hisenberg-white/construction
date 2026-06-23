from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse

from core.forms import DateInput, TenantModelForm, vehicle_label

from .models import DeliveryLog, SaleInvoice, SaleInvoiceLine


class SaleInvoiceForm(TenantModelForm):
    class Meta:
        model = SaleInvoice
        fields = ['depot', 'customer', 'invoice_no', 'invoice_date',
                  'additional_charges', 'discount', 'tax', 'paid', 'notes', 'reference_image']
        widgets = {'invoice_date': DateInput(), 'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, can_add_party=False, **kwargs):
        super().__init__(*args, **kwargs)
        if can_add_party:
            # Enable the inline "+ New customer" quick-add on the dropdown.
            self.fields['customer'].widget.attrs.update({
                'data-quick-add-url': reverse('parties:customer_quick_create'),
                'data-quick-add-label': 'Customer',
            })


class SaleInvoiceLineForm(TenantModelForm):
    class Meta:
        model = SaleInvoiceLine
        fields = ['material', 'service', 'vehicle', 'description',
                  'qty', 'unit', 'rate']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pick the actual vehicle; show its per-load capacity (SRS FR-05).
        self.fields['vehicle'].label_from_instance = vehicle_label
        self.fields['vehicle'].widget.attrs['data-vehicle-select'] = '1'
        # Clear model defaults (0) so blank extra rows stay unchanged/skipped.
        self.fields['qty'].initial = None
        self.fields['rate'].initial = None


SaleInvoiceLineFormSet = inlineformset_factory(
    SaleInvoice, SaleInvoiceLine, form=SaleInvoiceLineForm,
    extra=1, can_delete=True,  # start with one row; "+ Add item" adds more
)


class DeliveryLogForm(TenantModelForm):
    class Meta:
        model = DeliveryLog
        fields = ['method', 'recipient']
