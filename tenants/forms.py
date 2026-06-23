from core.forms import BootstrapFormMixin, DateInput, TenantModelForm
from django import forms

from .models import DepotLocation, TenantCompany, TenantEmailConfig


class TenantCompanyForm(BootstrapFormMixin, forms.ModelForm):
    """SaaS-owner form to create/edit a client company (tenant)."""

    class Meta:
        model = TenantCompany
        fields = ['name', 'registration_no', 'phone', 'email', 'address',
                  'default_currency', 'invoice_prefix', 'current_plan',
                  'subscription_status', 'subscription_start', 'subscription_end',
                  'is_active']
        widgets = {
            'subscription_start': DateInput(),
            'subscription_end': DateInput(),
            'address': forms.Textarea(attrs={'rows': 2}),
        }


class CompanySettingsForm(BootstrapFormMixin, forms.ModelForm):
    """Tenant-owner form to edit their own company profile (SRS FR-01)."""

    class Meta:
        model = TenantCompany
        fields = ['name', 'logo', 'registration_no', 'phone', 'email', 'address',
                  'default_currency', 'invoice_prefix', 'default_calendar']
        widgets = {'address': forms.Textarea(attrs={'rows': 2})}


class DepotForm(TenantModelForm):
    class Meta:
        model = DepotLocation
        fields = ['name', 'address', 'contact_person', 'phone',
                  'opening_balance', 'is_active']
        widgets = {'address': forms.Textarea(attrs={'rows': 2})}


class EmailConfigForm(BootstrapFormMixin, forms.ModelForm):
    """Per-tenant SMTP settings used to email invoices (SRS FR-16)."""

    class Meta:
        model = TenantEmailConfig
        fields = ['host', 'port', 'username', 'password', 'use_tls', 'use_ssl',
                  'from_email', 'from_name', 'is_active']
        widgets = {'password': forms.PasswordInput(render_value=True)}
