"""StockService — the single entry point for all stock movements (SRS FR-09, 12.2).

Stock is append-only: every change is a new :class:`StockLedger` row with a
running ``balance_after``. All callers (purchases, sales, splits, adjustments)
must go through here so balances can never be corrupted.
"""
import json
from decimal import Decimal

from django.db import models, transaction
from django.db.models import Sum

from .models import MaterialItem, StockLedger, Vehicle


def vehicle_capacity_json(tenant):
    """JSON map of vehicle pk -> {name, capacity, unit} for a tenant.

    Capacity is taken from each vehicle's type. Used by the purchase/sale forms
    to suggest a quantity from the selected vehicle's per-load capacity and show
    load conversions (SRS FR-05, 6.1).
    """
    data = {}
    if tenant is not None:
        vehicles = (Vehicle.objects.for_tenant(tenant)
                    .filter(is_active=True).select_related('vehicle_type'))
        for v in vehicles:
            vt = v.vehicle_type
            data[str(v.pk)] = {
                'name': str(v),
                'capacity': str(vt.default_capacity) if vt else '',
                'unit': vt.capacity_unit if vt else '',
            }
    return json.dumps(data)

IN_TYPES = {
    StockLedger.TransactionType.PURCHASE,
    StockLedger.TransactionType.PURCHASE_EXCESS,
    StockLedger.TransactionType.TRANSFER_IN,
    StockLedger.TransactionType.ADJUST_IN,
}


class StockService:
    @staticmethod
    def on_hand(tenant, depot=None):
        """Current quantity per (depot_id, material_id) from all movements."""
        qs = StockLedger.objects.for_tenant(tenant)
        if depot is not None:
            qs = qs.filter(depot=depot)
        rows = qs.values('depot_id', 'material_id').annotate(i=Sum('qty_in'), o=Sum('qty_out'))
        return {(r['depot_id'], r['material_id']): (r['i'] or 0) - (r['o'] or 0) for r in rows}

    @staticmethod
    def low_stock(tenant):
        """Stock-tracked materials at/below their reorder level (or negative),
        as a list of dicts, most serious first."""
        from tenants.models import DepotLocation
        balances = StockService.on_hand(tenant)
        materials = MaterialItem.objects.for_tenant(tenant).filter(is_active=True, stock_enabled=True)
        depots = DepotLocation.objects.filter(tenant=tenant, is_active=True)
        alerts = []
        for m in materials:
            for d in depots:
                qty = balances.get((d.pk, m.pk))
                if qty is None and not m.reorder_level:
                    continue  # never stocked here and no minimum set
                qty = qty or Decimal('0')
                if qty < 0 or (m.reorder_level and qty <= m.reorder_level):
                    alerts.append({'material': m, 'depot': d, 'qty': qty,
                                   'reorder_level': m.reorder_level,
                                   'status': 'negative' if qty < 0 else ('out' if qty == 0 else 'low')})
        severity = {'negative': 0, 'out': 1, 'low': 2}
        alerts.sort(key=lambda a: (severity[a['status']], a['qty'] - a['reorder_level']))
        return alerts

    @staticmethod
    def current_balance(tenant, depot, material):
        """Latest closing balance for a depot+material (0 if no movements)."""
        last = (
            StockLedger.objects.for_tenant(tenant)
            .filter(depot=depot, material=material)
            .order_by('-created_at', '-id')
            .first()
        )
        return last.balance_after if last else Decimal('0')

    @staticmethod
    @transaction.atomic
    def record_movement(*, tenant, depot, material, transaction_type, qty,
                        reference_type='', reference_id=None, note='', actor=None):
        """Post a single stock movement and return the new ledger row.

        ``qty`` is always positive; direction is derived from ``transaction_type``.
        """
        qty = Decimal(qty)
        is_in = transaction_type in IN_TYPES
        balance = StockService.current_balance(tenant, depot, material)
        balance = balance + qty if is_in else balance - qty
        return StockLedger.objects.create(
            tenant=tenant,
            depot=depot,
            material=material,
            transaction_type=transaction_type,
            qty_in=qty if is_in else Decimal('0'),
            qty_out=Decimal('0') if is_in else qty,
            balance_after=balance,
            reference_type=reference_type,
            reference_id=reference_id,
            note=note,
            created_by=actor,
            updated_by=actor,
        )

    @staticmethod
    def convert_quantity(rule, from_qty):
        """Convert a load quantity using a VehicleCapacityRule (SRS 6.1)."""
        return Decimal(from_qty) * rule.conversion_factor
