from django.urls import path

from core.crud import crud_urlpatterns

from . import views

app_name = 'parties'

urlpatterns = [
    # Inline AJAX quick-create used by purchase/sale entry forms.
    path('app/customers/quick-add/', views.customer_quick_create, name='customer_quick_create'),
    path('app/suppliers/quick-add/', views.supplier_quick_create, name='supplier_quick_create'),

    *crud_urlpatterns(
        'app/customers', 'customer',
        list=views.CustomerListView, create=views.CustomerCreateView,
        detail=views.CustomerDetailView, update=views.CustomerUpdateView,
        delete=views.CustomerDeleteView,
    ),
    *crud_urlpatterns(
        'app/suppliers', 'supplier',
        list=views.SupplierListView, create=views.SupplierCreateView,
        detail=views.SupplierDetailView, update=views.SupplierUpdateView,
        delete=views.SupplierDeleteView,
    ),
]
