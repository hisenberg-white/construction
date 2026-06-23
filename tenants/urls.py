from django.urls import path

from core.crud import crud_urlpatterns

from . import views

app_name = 'tenants'

urlpatterns = [
    # SaaS owner: client companies (SRS 12.3 /saas-admin/clients/).
    *crud_urlpatterns(
        'saas-admin/clients', 'client',
        list=views.ClientListView, create=views.ClientCreateView,
        detail=views.ClientDetailView, update=views.ClientUpdateView,
        delete=views.ClientDeleteView,
    ),
    # Tenant: depots (SRS 12.3 /app/depots/).
    *crud_urlpatterns(
        'app/depots', 'depot',
        list=views.DepotListView, create=views.DepotCreateView,
        detail=views.DepotDetailView, update=views.DepotUpdateView,
        delete=views.DepotDeleteView,
    ),
    # Tenant: company settings + per-tenant SMTP email settings.
    path('app/company-settings/', views.CompanySettingsView.as_view(), name='company_settings'),
    path('app/email-settings/', views.EmailConfigView.as_view(), name='email_settings'),
    # SaaS owner: choose which company to work in.
    path('app/set-company/', views.set_acting_company, name='set_company'),
]
