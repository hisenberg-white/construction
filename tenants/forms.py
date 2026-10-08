from core.forms import BootstrapFormMixin, DateInput, TenantModelForm
from django import forms

from .models import DepotLocation, TenantCompany, TenantEmailConfig, TenantMessagingConfig


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


class MessagingConfigForm(BootstrapFormMixin, forms.ModelForm):
    """Per-tenant SMS / WhatsApp gateway settings used to send invoices (SRS FR-16)."""

    class Meta:
        model = TenantMessagingConfig
        fields = ['country_code',
                  'sms_enabled', 'sms_provider', 'sms_token', 'sms_account_sid', 'sms_sender',
                  'whatsapp_enabled', 'whatsapp_provider', 'whatsapp_token',
                  'whatsapp_account_sid', 'whatsapp_sender',
                  'whatsapp_template', 'whatsapp_template_language']
        widgets = {'sms_token': forms.PasswordInput(render_value=True),
                   'whatsapp_token': forms.PasswordInput(render_value=True)}

    def clean_country_code(self):
        code = (self.cleaned_data.get('country_code') or '').strip().lstrip('+')
        if not code.isdigit():
            raise forms.ValidationError('Digits only, e.g. 977.')
        return code

    def clean(self):
        data = super().clean()
        if data.get('sms_enabled'):
            provider = data.get('sms_provider')
            if not data.get('sms_token'):
                self.add_error('sms_token', 'Required when SMS is enabled.')
            if provider == 'sparrow' and not data.get('sms_sender'):
                self.add_error('sms_sender', 'Sparrow SMS needs your sender identity.')
            if provider == 'twilio':
                if not data.get('sms_account_sid'):
                    self.add_error('sms_account_sid', 'Required for Twilio.')
                if not data.get('sms_sender'):
                    self.add_error('sms_sender', 'Required for Twilio (your Twilio number).')
        if data.get('whatsapp_enabled'):
            if not data.get('whatsapp_token'):
                self.add_error('whatsapp_token', 'Required when WhatsApp is enabled.')
            if not data.get('whatsapp_sender'):
                self.add_error('whatsapp_sender', 'Required when WhatsApp is enabled.')
            if (data.get('whatsapp_provider') == 'twilio'
                    and not data.get('whatsapp_account_sid')):
                self.add_error('whatsapp_account_sid', 'Required for Twilio.')
        return data
