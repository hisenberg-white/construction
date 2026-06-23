"""Customer & supplier CRUD (SRS FR-06, module 'parties')."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core import permissions
from core.crud import (
    CrudCreateView,
    CrudDeleteView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
)

from .forms import CustomerForm, SupplierForm
from .models import Customer, Supplier

MODULE = permissions.PARTIES


# --- Inline quick-create (AJAX) ----------------------------------------------
# Lets a user register a brand-new customer/supplier without leaving a
# purchase/sale entry. Tenant-scoped and gated on the parties-create permission.
def _quick_create_party(request, model):
    if not permissions.has_perm(request.user, MODULE, 'c'):
        return JsonResponse({'ok': False, 'error': 'You are not allowed to add this.'}, status=403)
    tenant = getattr(request, 'tenant', None)
    if tenant is None:
        return JsonResponse({'ok': False, 'error': 'No company is linked to your account.'}, status=400)
    name = (request.POST.get('name') or '').strip()
    if not name:
        return JsonResponse({'ok': False, 'error': 'Name is required.'}, status=400)
    obj = model.objects.create(
        tenant=tenant, name=name, phone=(request.POST.get('phone') or '').strip(),
        created_by=request.user, updated_by=request.user,
    )
    return JsonResponse({'ok': True, 'id': obj.pk, 'label': str(obj)})


@login_required
@require_POST
def customer_quick_create(request):
    return _quick_create_party(request, Customer)


@login_required
@require_POST
def supplier_quick_create(request):
    return _quick_create_party(request, Supplier)


# --- Customers ---------------------------------------------------------------
class CustomerListView(CrudListView):
    model = Customer
    permission_module = MODULE
    crud_basename = 'customer'
    list_display = ['name', 'phone', 'credit_limit', 'opening_balance', 'is_active']


class CustomerDetailView(CrudDetailView):
    model = Customer
    permission_module = MODULE
    crud_basename = 'customer'
    list_display = ['name', 'phone', 'email', 'address',
                    'credit_limit', 'opening_balance', 'is_active']


class CustomerCreateView(CrudCreateView):
    model = Customer
    permission_module = MODULE
    crud_basename = 'customer'
    form_class = CustomerForm


class CustomerUpdateView(CrudUpdateView):
    model = Customer
    permission_module = MODULE
    crud_basename = 'customer'
    form_class = CustomerForm


class CustomerDeleteView(CrudDeleteView):
    model = Customer
    permission_module = MODULE
    crud_basename = 'customer'
    list_display = ['name']


# --- Suppliers ---------------------------------------------------------------
class SupplierListView(CrudListView):
    model = Supplier
    permission_module = MODULE
    crud_basename = 'supplier'
    list_display = ['name', 'supplier_type', 'phone', 'opening_balance', 'is_active']


class SupplierDetailView(CrudDetailView):
    model = Supplier
    permission_module = MODULE
    crud_basename = 'supplier'
    list_display = ['name', 'supplier_type', 'phone', 'email', 'address',
                    'opening_balance', 'is_active']


class SupplierCreateView(CrudCreateView):
    model = Supplier
    permission_module = MODULE
    crud_basename = 'supplier'
    form_class = SupplierForm


class SupplierUpdateView(CrudUpdateView):
    model = Supplier
    permission_module = MODULE
    crud_basename = 'supplier'
    form_class = SupplierForm


class SupplierDeleteView(CrudDeleteView):
    model = Supplier
    permission_module = MODULE
    crud_basename = 'supplier'
    list_display = ['name']
