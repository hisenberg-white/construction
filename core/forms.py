"""Form helpers — Bootstrap styling and tenant-scoped relation fields."""
from django import forms
from django.utils import timezone


class DateInput(forms.DateInput):
    """HTML5 date picker that round-trips ISO dates."""

    input_type = 'date'

    def __init__(self, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(**kwargs)


def vehicle_label(vehicle):
    """Dropdown label for a specific vehicle, incl. its per-load capacity (FR-05)."""
    vt = vehicle.vehicle_type
    if vt and vt.default_capacity is not None:
        return f'{vehicle} — {vt.name} (1 load ≈ {vt.default_capacity:g} {vt.capacity_unit})'
    return str(vehicle)


class BootstrapFormMixin:
    """Apply Bootstrap 5 classes to all widgets of a form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = timezone.localdate()
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')
                # Keep text areas compact by default (Django defaults to a
                # 10-row box). Honour any explicit, non-default row count.
                if isinstance(widget, forms.Textarea):
                    if str(widget.attrs.get('rows', '')) in ('', '10'):
                        widget.attrs['rows'] = 3
            # Default date pickers to today on new (unbound) forms, without
            # overwriting a value being edited.
            if isinstance(widget, DateInput) and not self.is_bound:
                if self.initial.get(name) in (None, ''):
                    self.initial[name] = today

            # Friendly "Select …" placeholder instead of the default "---------".
            label_text = (field.label or name.replace('_', ' ')).lower()
            placeholder = f'Select {label_text}'
            if (isinstance(field, forms.ModelChoiceField)
                    and not isinstance(field, forms.ModelMultipleChoiceField)):
                if field.empty_label is not None:
                    field.empty_label = placeholder
            elif (isinstance(field, forms.ChoiceField)
                  and isinstance(widget, forms.Select)
                  and not isinstance(widget, forms.SelectMultiple)):
                choices = list(field.choices)
                if choices and choices[0][0] in ('', None):
                    choices[0] = (choices[0][0], placeholder)
                    field.choices = choices


class TenantModelForm(BootstrapFormMixin, forms.ModelForm):
    """ModelForm that scopes foreign-key choices to the current tenant.

    Pass ``tenant=`` when instantiating; any FK whose related model carries a
    ``tenant`` field is filtered so users never see another tenant's records
    (SRS 12.2).
    """

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)
        if tenant is None:
            return
        for name, field in self.fields.items():
            queryset = getattr(field, 'queryset', None)
            if queryset is None:
                continue
            model = queryset.model
            if any(f.name == 'tenant' for f in model._meta.fields):
                field.queryset = queryset.filter(tenant=tenant)
