"""Root URL configuration for DepotLedger SaaS.

Each app owns its full path prefixes (mounted at root) so URL names resolve
under clean namespaces. Layout follows SRS section 12.3:

* ``/admin/``        — Django admin
* ``/accounts/...``  — authentication + user/role management
* ``/app/...``       — tenant application (masters, operations, reports)
* ``/saas-admin/...``— SaaS owner: clients, plans, subscriptions
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # set_language view
    path('', include('accounts.urls')),
    path('', include('reports.urls')),
    path('', include('tenants.urls')),
    path('', include('subscriptions.urls')),
    path('', include('inventory.urls')),
    path('', include('parties.urls')),
    path('', include('purchases.urls')),
    path('', include('sales.urls')),
    path('', include('ledger.urls')),
    path('', include('expenses.urls')),
    path('', include('employees.urls')),
    path('', include('audit.urls')),

    path('', RedirectView.as_view(pattern_name='reports:dashboard', permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
