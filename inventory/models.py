"""Item master, vehicles, capacity-conversion rules and stock ledger.

Covers SRS FR-04 (items), FR-05 (vehicles & capacity), FR-09 (stock) and
section 6 (material/vehicle/stock conversion rules).
"""
from django.db import models

from core.models import TenantOwnedModel


class MaterialItem(TenantOwnedModel):
    """Sellable, stock-affecting material (sand, brick, aggregate…) — FR-04."""

    name = models.CharField(max_length=120)
    category = models.CharField(max_length=80, blank=True)
    # Internal stock is always held in one base unit per material (SRS 6.1).
    base_unit = models.CharField(
        max_length=40,
        default='cubic_feet',
        help_text='Base unit for internal stock, e.g. cubic feet, brass, ton, Nissan-load.',
    )
    default_purchase_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    default_sale_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    stock_enabled = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_material_per_tenant'
            ),
        ]

    def __str__(self):
        return self.name


class ServiceItem(TenantOwnedModel):
    """Non-stock service such as JCB hourly work (SRS FR-04, FR-11)."""

    class UnitType(models.TextChoices):
        HOUR = 'hour', 'Hour'
        DAY = 'day', 'Day'
        TRIP = 'trip', 'Trip'

    name = models.CharField(max_length=120)
    unit_type = models.CharField(max_length=10, choices=UnitType.choices, default=UnitType.HOUR)
    default_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class VehicleType(TenantOwnedModel):
    """A vehicle category (Tipper, Eicher, Nissan…) with a base capacity — FR-05."""

    name = models.CharField(max_length=80)
    default_capacity = models.DecimalField(
        max_digits=12, decimal_places=3, default=1,
        help_text='Standard capacity expressed in the capacity unit.',
    )
    capacity_unit = models.CharField(max_length=40, default='cubic_feet')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_vehicletype_per_tenant'
            ),
        ]

    def __str__(self):
        return self.name


class Vehicle(TenantOwnedModel):
    """An individual physical vehicle/equipment, for per-vehicle P/L (SRS FR-13)."""

    vehicle_type = models.ForeignKey(
        VehicleType, on_delete=models.PROTECT, related_name='vehicles'
    )
    name = models.CharField(max_length=120, help_text='Plate number or nickname.')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class VehicleCapacityRule(TenantOwnedModel):
    """Conversion factor between vehicle loads (e.g. 1 Tipper = 3 Nissan) — SRS 6.1."""

    material = models.ForeignKey(
        MaterialItem, on_delete=models.CASCADE, related_name='capacity_rules',
        null=True, blank=True,
        help_text='Leave blank for a general rule that applies to all materials.',
    )
    from_vehicle_type = models.ForeignKey(
        VehicleType, on_delete=models.CASCADE, related_name='conversion_from'
    )
    to_vehicle_type = models.ForeignKey(
        VehicleType, on_delete=models.CASCADE, related_name='conversion_to',
        null=True, blank=True,
        help_text='Target vehicle; blank means conversion to the material base unit.',
    )
    conversion_factor = models.DecimalField(
        max_digits=10, decimal_places=4,
        help_text='1 from-vehicle = factor × to-vehicle/base-unit.',
    )

    class Meta:
        ordering = ['from_vehicle_type']

    def __str__(self):
        target = self.to_vehicle_type or self.material.base_unit if self.material else 'base unit'
        return f'1 {self.from_vehicle_type} = {self.conversion_factor} {target}'


class StockLedger(TenantOwnedModel):
    """Append-only stock movement ledger per depot+material (SRS FR-09).

    Stock is never edited in place — every change is a new row with a running
    ``balance_after`` so opening/closing positions are auditable.
    """

    class TransactionType(models.TextChoices):
        PURCHASE = 'purchase', 'Purchase In'
        PURCHASE_EXCESS = 'purchase_excess', 'Split/Excess In'
        TRANSFER_IN = 'transfer_in', 'Transfer In'
        ADJUST_IN = 'adjust_in', 'Adjustment In'
        SALE = 'sale', 'Sale Out'
        TRANSFER_OUT = 'transfer_out', 'Transfer Out'
        DAMAGE = 'damage', 'Damage / Loss Out'
        ADJUST_OUT = 'adjust_out', 'Adjustment Out'

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.PROTECT, related_name='stock_entries'
    )
    material = models.ForeignKey(
        MaterialItem, on_delete=models.PROTECT, related_name='stock_entries'
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    # Generic reference to the source document (purchase, invoice, adjustment…).
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    qty_in = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    qty_out = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    balance_after = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'depot', 'material', 'created_at']),
        ]

    def __str__(self):
        return f'{self.material} @ {self.depot}: {self.get_transaction_type_display()}'
