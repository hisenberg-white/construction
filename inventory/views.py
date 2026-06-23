"""Inventory CRUD: item/vehicle masters (module 'items'), stock ledger and
manual stock adjustments (module 'stock'). SRS FR-04, FR-05, FR-09, section 6.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from core import permissions
from core.crud import (
    CrudContextMixin,
    CrudCreateView,
    CrudDeleteView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
    PermissionRequiredMixin,
    TenantRequiredMixin,
)
from tenants.models import DepotLocation

from .forms import (
    MaterialItemForm,
    ServiceItemForm,
    StockAdjustmentForm,
    VehicleCapacityRuleForm,
    VehicleForm,
    VehicleTypeForm,
)
from .models import (
    MaterialItem,
    ServiceItem,
    StockLedger,
    Vehicle,
    VehicleCapacityRule,
    VehicleType,
)
from .services import StockService

ITEMS = permissions.ITEMS
STOCK = permissions.STOCK


def _crud_set(model_, form_, basename, display, *, module=ITEMS, delete_list=None):
    """Generate the five CRUD view classes for a simple master model."""
    ns = {'model': model_, 'permission_module': module, 'crud_basename': basename}
    list_v = type(f'{basename}ListView', (CrudListView,), {**ns, 'list_display': display})
    detail_v = type(f'{basename}DetailView', (CrudDetailView,), {**ns, 'list_display': display})
    create_v = type(f'{basename}CreateView', (CrudCreateView,), {**ns, 'form_class': form_})
    update_v = type(f'{basename}UpdateView', (CrudUpdateView,), {**ns, 'form_class': form_})
    delete_v = type(f'{basename}DeleteView', (CrudDeleteView,),
                    {**ns, 'list_display': delete_list or display[:1]})
    return list_v, create_v, detail_v, update_v, delete_v


(MaterialListView, MaterialCreateView, MaterialDetailView,
 MaterialUpdateView, MaterialDeleteView) = _crud_set(
    MaterialItem, MaterialItemForm, 'material',
    ['name', 'category', 'base_unit', 'default_sale_rate', 'stock_enabled', 'is_active'])

(ServiceListView, ServiceCreateView, ServiceDetailView,
 ServiceUpdateView, ServiceDeleteView) = _crud_set(
    ServiceItem, ServiceItemForm, 'service',
    ['name', 'unit_type', 'default_rate', 'is_active'])

(VehicleTypeListView, VehicleTypeCreateView, VehicleTypeDetailView,
 VehicleTypeUpdateView, VehicleTypeDeleteView) = _crud_set(
    VehicleType, VehicleTypeForm, 'vehicletype',
    ['name', 'default_capacity', 'capacity_unit', 'is_active'])

(VehicleListView, VehicleCreateView, VehicleDetailView,
 VehicleUpdateView, VehicleDeleteView) = _crud_set(
    Vehicle, VehicleForm, 'vehicle',
    ['name', 'vehicle_type', 'is_active'])

(CapacityRuleListView, CapacityRuleCreateView, CapacityRuleDetailView,
 CapacityRuleUpdateView, CapacityRuleDeleteView) = _crud_set(
    VehicleCapacityRule, VehicleCapacityRuleForm, 'capacityrule',
    ['from_vehicle_type', 'to_vehicle_type', 'material', 'conversion_factor'])


# --- Stock ledger (read-only) + adjustment -----------------------------------
class StockLedgerBookView(TenantRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Stock movements styled like a ledger book (SRS FR-09).

    Date filter defaults to the last month; optional depot + material filters.
    When a single depot+material is chosen, the closing balance carried from
    before the range is shown as the Opening Balance.
    """

    permission_module = STOCK
    permission_action = 'r'
    crud_basename = 'stock'
    template_name = 'inventory/stock_ledger.html'

    def _parse_date(self, key, default):
        try:
            return timezone.datetime.strptime(self.request.GET.get(key, ''), '%Y-%m-%d').date()
        except ValueError:
            return default

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        today = timezone.localdate()
        date_from = self._parse_date('from', today - timedelta(days=30))
        date_to = self._parse_date('to', today)
        depot_id = self.request.GET.get('depot') or ''
        material_id = self.request.GET.get('material') or ''

        qs = StockLedger.objects.all()
        if tenant is not None:
            qs = qs.for_tenant(tenant)
        qs = qs.select_related('depot', 'material')
        if depot_id.isdigit():
            qs = qs.filter(depot_id=int(depot_id))
        if material_id.isdigit():
            qs = qs.filter(material_id=int(material_id))

        single = depot_id.isdigit() and material_id.isdigit()
        opening = None
        if single:
            prior = qs.filter(created_at__date__lt=date_from).order_by('-created_at', '-id').first()
            opening = prior.balance_after if prior else Decimal('0')

        rows = qs.filter(created_at__date__gte=date_from, created_at__date__lte=date_to) \
                 .order_by('created_at', 'id')
        totals = rows.aggregate(i=Sum('qty_in'), o=Sum('qty_out'))
        context.update({
            'company': tenant,
            'entries': rows,
            'date_from': date_from, 'date_to': date_to,
            'depots': DepotLocation.objects.filter(tenant=tenant) if tenant else DepotLocation.objects.none(),
            'materials': MaterialItem.objects.filter(tenant=tenant) if tenant else MaterialItem.objects.none(),
            'depot_id': depot_id, 'material_id': material_id,
            'single_account': single, 'opening_balance': opening,
            'total_in': totals['i'] or 0, 'total_out': totals['o'] or 0,
            'can_adjust': permissions.has_perm(self.request.user, STOCK, 'c'),
        })
        return context


class StockLedgerDetailView(CrudDetailView):
    model = StockLedger
    permission_module = STOCK
    crud_basename = 'stock'
    list_display = ['created_at', 'depot', 'material', 'transaction_type',
                    'qty_in', 'qty_out', 'balance_after', 'reference_type',
                    'reference_id', 'note']


class StockAdjustmentView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin, FormView):
    model = StockLedger
    permission_module = STOCK
    permission_action = 'c'
    crud_basename = 'stock'
    template_name = 'core/object_form.html'
    form_class = StockAdjustmentForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['verbose_name'] = 'Stock Adjustment'
        return context

    def form_valid(self, form):
        data = form.cleaned_data
        entry = StockService.record_movement(
            tenant=self.request.tenant,
            depot=data['depot'],
            material=data['material'],
            transaction_type=data['transaction_type'],
            qty=data['qty'],
            reference_type='manual_adjustment',
            note=data['note'],
            actor=self.request.user,
        )
        from audit.services import log_action
        log_action(self.request, 'create', instance=entry,
                   after={'type': entry.get_transaction_type_display(),
                          'material': str(data['material']), 'qty': str(data['qty'])})
        messages.success(self.request, 'Stock adjustment posted.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(self.crud_url_name('list'))
