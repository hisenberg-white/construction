from django import forms
from django.forms import inlineformset_factory
from django.urls import reverse

from core.forms import DateInput, TenantModelForm, vehicle_label

from .models import Purchase, PurchaseExpense, Trip


class PurchaseForm(TenantModelForm):
    class Meta:
        model = Purchase
        # Additional costs (petrol, transport, unloading…) are entered as
        # dynamic expense lines below rather than fixed fields (SRS FR-07).
        fields = ['depot', 'supplier', 'material', 'vehicle', 'purchase_date',
                  'reference_no', 'qty', 'rate', 'paid_amount', 'notes', 'reference_image']
        widgets = {'purchase_date': DateInput(), 'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, can_add_party=False, **kwargs):
        super().__init__(*args, **kwargs)
        # Pick the actual vehicle; show its per-load capacity (SRS FR-05).
        self.fields['vehicle'].label_from_instance = vehicle_label
        self.fields['vehicle'].widget.attrs['data-vehicle-select'] = '1'
        if can_add_party:
            # Enable the inline "+ New supplier" quick-add on the dropdown.
            self.fields['supplier'].widget.attrs.update({
                'data-quick-add-url': reverse('parties:supplier_quick_create'),
                'data-quick-add-label': 'Supplier',
            })


class PurchaseExpenseForm(TenantModelForm):
    class Meta:
        model = PurchaseExpense
        fields = ['category', 'amount', 'note']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Clear the model default (0) so blank extra rows stay "unchanged" and
        # aren't validated as required (Django inline-formset gotcha).
        self.fields['amount'].initial = None
        # Quick-add a new expense category (e.g. Petrol) without leaving the form.
        self.fields['category'].widget.attrs.update({
            'data-quick-add-url': reverse('expenses:category_quick_create'),
            'data-quick-add-label': 'Expense Category',
        })


PurchaseExpenseFormSet = inlineformset_factory(
    Purchase, PurchaseExpense, form=PurchaseExpenseForm, extra=3, can_delete=True)


class TripForm(TenantModelForm):
    class Meta:
        model = Trip
        fields = ['depot', 'purchase', 'material', 'vehicle', 'source',
                  'total_qty', 'sold_qty', 'excess_qty', 'trip_status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle'].label_from_instance = vehicle_label


class TripForm(TenantModelForm):
    class Meta:
        model = Trip
        fields = ['depot', 'purchase', 'material', 'vehicle', 'source',
                  'total_qty', 'sold_qty', 'excess_qty', 'trip_status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vehicle'].label_from_instance = vehicle_label
