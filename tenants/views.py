"""Tenant company (SaaS), depot and company-settings views.

* Clients (TenantCompany) — SaaS owner area, module 'saas' (SRS section 8).
* Depots — tenant area, module 'company_settings' (SRS FR-02).
* Company settings — tenant owner edits their own company (SRS FR-01).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView

from core import permissions
from core.crud import (
    CrudContextMixin,
    CrudCreateView,
    CrudDeleteView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
    PermissionRequiredMixin,
    SaaSCreateView,
    SaaSDeleteView,
    SaaSDetailView,
    SaaSListView,
    SaaSUpdateView,
)

from .forms import CompanySettingsForm, DepotForm, EmailConfigForm, TenantCompanyForm
from .models import DepotLocation, TenantCompany, TenantEmailConfig


@login_required
@require_POST
def set_acting_company(request):
    """SaaS owner / superuser chooses which company to work in (data entry,
    dashboards). Stored in the session; normal tenant users are unaffected."""
    if not (request.user.is_superuser or getattr(request.user, 'is_saas_staff', False)):
        return redirect('reports:dashboard')
    company_id = request.POST.get('company') or ''
    if company_id.isdigit() and TenantCompany.objects.filter(pk=company_id, is_active=True).exists():
        request.session['acting_tenant_id'] = int(company_id)
    else:
        request.session.pop('acting_tenant_id', None)
    return redirect(request.POST.get('next') or 'reports:dashboard')


# --- SaaS: client companies --------------------------------------------------
class ClientListView(SaaSListView):
    model = TenantCompany
    crud_basename = 'client'
    list_display = ['name', 'subscription_status', 'current_plan',
                    'subscription_end', 'is_active']
    title = 'SaaS Clients'


class ClientDetailView(SaaSDetailView):
    model = TenantCompany
    crud_basename = 'client'
    list_display = ['name', 'registration_no', 'phone', 'email', 'address',
                    'default_currency', 'invoice_prefix', 'current_plan',
                    'subscription_status', 'subscription_start',
                    'subscription_end', 'is_active']


class ClientCreateView(SaaSCreateView):
    model = TenantCompany
    crud_basename = 'client'
    form_class = TenantCompanyForm


class ClientUpdateView(SaaSUpdateView):
    model = TenantCompany
    crud_basename = 'client'
    form_class = TenantCompanyForm


class ClientDeleteView(SaaSDeleteView):
    model = TenantCompany
    crud_basename = 'client'
    list_display = ['name']


# --- Tenant: depots ----------------------------------------------------------
class DepotListView(CrudListView):
    model = DepotLocation
    permission_module = permissions.COMPANY_SETTINGS
    crud_basename = 'depot'
    list_display = ['name', 'contact_person', 'phone', 'opening_balance', 'is_active']


class DepotDetailView(CrudDetailView):
    model = DepotLocation
    permission_module = permissions.COMPANY_SETTINGS
    crud_basename = 'depot'
    list_display = ['name', 'address', 'contact_person', 'phone',
                    'opening_balance', 'is_active']


class DepotCreateView(CrudCreateView):
    model = DepotLocation
    permission_module = permissions.COMPANY_SETTINGS
    crud_basename = 'depot'
    form_class = DepotForm


class DepotUpdateView(CrudUpdateView):
    model = DepotLocation
    permission_module = permissions.COMPANY_SETTINGS
    crud_basename = 'depot'
    form_class = DepotForm


class DepotDeleteView(CrudDeleteView):
    model = DepotLocation
    permission_module = permissions.COMPANY_SETTINGS
    crud_basename = 'depot'
    list_display = ['name']


# --- Tenant: company settings (edit own company) -----------------------------
class CompanySettingsView(PermissionRequiredMixin, CrudContextMixin, UpdateView):
    model = TenantCompany
    permission_module = permissions.COMPANY_SETTINGS
    permission_action = 'u'
    crud_basename = 'depot'  # reuse depot list as the "back" target
    form_class = CompanySettingsForm
    template_name = 'core/object_form.html'

    def dispatch(self, request, *args, **kwargs):
        # SaaS staff have no single "own company" to edit — send them to clients.
        if request.user.is_authenticated and request.tenant is None:
            messages.info(request, 'Select a client company to edit its settings.')
            return redirect('tenants:client_list')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.request.tenant

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = 'Company Settings'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Company settings saved.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reports:dashboard')


class EmailConfigView(PermissionRequiredMixin, CrudContextMixin, UpdateView):
    """Edit the tenant's SMTP email settings (SRS FR-16)."""

    model = TenantEmailConfig
    permission_module = permissions.COMPANY_SETTINGS
    permission_action = 'u'
    crud_basename = 'depot'
    form_class = EmailConfigForm
    template_name = 'core/object_form.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.tenant is None:
            messages.info(request, 'Email settings are configured per company.')
            return redirect('tenants:client_list')
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        config, _ = TenantEmailConfig.objects.get_or_create(
            tenant=self.request.tenant,
            defaults={'host': '', 'from_email': ''})
        return config

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = 'Email (SMTP) Settings'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Email settings saved.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('reports:dashboard')
