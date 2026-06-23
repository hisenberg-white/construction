"""Purchase records and incoming trips / load splits (SRS FR-07, FR-10)."""
from decimal import Decimal

from django.db import models

from core.constants import PaymentStatus
from core.models import CancellableModel, TenantOwnedModel


class Purchase(TenantOwnedModel, CancellableModel):
    """A material purchase from a supplier (SRS FR-07).

    Trip/transport/loading costs can be capitalised into the material cost for
    accurate per-load profit (SRS 7.3).
    """

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.PROTECT, related_name='purchases'
    )
    supplier = models.ForeignKey(
        'parties.Supplier', on_delete=models.PROTECT, related_name='purchases'
    )
    material = models.ForeignKey(
        'inventory.MaterialItem', on_delete=models.PROTECT, related_name='purchases'
    )
    vehicle_type = models.ForeignKey(
        'inventory.VehicleType', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='purchases',
    )
    # The actual vehicle used, for per-vehicle job tracking (SRS FR-05, FR-13).
    vehicle = models.ForeignKey(
        'inventory.Vehicle', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='purchases',
    )
    purchase_date = models.DateField()
    reference_no = models.CharField(max_length=80, blank=True)

    # Quantity is stored in the material base unit (after conversion/override).
    qty = models.DecimalField(max_digits=14, decimal_places=3)
    rate = models.DecimalField(max_digits=12, decimal_places=2)
    material_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # Direct costs that can be capitalised into cost-of-goods (SRS FR-07, 7.3).
    transport_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unloading_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    total_cost = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    notes = models.TextField(blank=True)
    reference_image = models.ImageField(
        upload_to='references/purchases/%Y/%m/', blank=True, null=True,
        help_text='Optional photo of the bill / reference.')

    class Meta:
        ordering = ['-purchase_date', '-id']
        indexes = [models.Index(fields=['tenant', 'depot', 'purchase_date'])]

    def _set_payment_status(self):
        paid = self.paid_amount or Decimal('0')
        if paid <= 0:
            self.payment_status = PaymentStatus.UNPAID
        elif paid >= (self.total_cost or 0):
            self.payment_status = PaymentStatus.PAID
        else:
            self.payment_status = PaymentStatus.PARTIAL

    def save(self, *args, **kwargs):
        # Base totals (excludes expense lines, which are saved after the
        # purchase — call recompute_costs() once they exist; SRS FR-07, 7.3).
        self.material_cost = (self.qty or 0) * (self.rate or 0)
        self.total_cost = (self.material_cost + (self.transport_cost or 0)
                           + (self.unloading_cost or 0) + (self.other_cost or 0))
        self._set_payment_status()
        super().save(*args, **kwargs)

    def recompute_costs(self, save=True):
        """Recalculate total cost including the dynamic expense lines (FR-07)."""
        self.material_cost = (self.qty or 0) * (self.rate or 0)
        extra = self.expense_lines.aggregate(s=models.Sum('amount'))['s'] or Decimal('0')
        self.total_cost = (self.material_cost + (self.transport_cost or 0)
                           + (self.unloading_cost or 0) + (self.other_cost or 0) + extra)
        self._set_payment_status()
        if save:
            super().save(update_fields=['material_cost', 'total_cost',
                                        'payment_status', 'updated_at'])

    @property
    def due_amount(self):
        return (self.total_cost or 0) - (self.paid_amount or 0)

    def __str__(self):
        return f'Purchase #{self.pk} — {self.material} from {self.supplier}'


class Trip(TenantOwnedModel, CancellableModel):
    """An incoming load that may be split between a sale and depot excess (FR-10)."""

    class TripStatus(models.TextChoices):
        OPEN = 'open', 'Open'
        SPLIT = 'split', 'Split Allocated'
        CLOSED = 'closed', 'Closed'

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.PROTECT, related_name='trips'
    )
    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name='trips',
        null=True, blank=True,
    )
    material = models.ForeignKey(
        'inventory.MaterialItem', on_delete=models.PROTECT, related_name='trips'
    )
    vehicle_type = models.ForeignKey(
        'inventory.VehicleType', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='trips',
    )
    vehicle = models.ForeignKey(
        'inventory.Vehicle', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='trips',
    )
    source = models.CharField(max_length=200, blank=True)
    total_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    sold_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    excess_qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    trip_status = models.CharField(
        max_length=10, choices=TripStatus.choices, default=TripStatus.OPEN
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Trip #{self.pk} — {self.material} ({self.get_trip_status_display()})'


class PurchaseExpense(models.Model):
    """An additional cost on a purchase (petrol, transport, labour…) chosen from
    a category dropdown — capitalised into the purchase's total cost (SRS FR-07)."""

    purchase = models.ForeignKey(
        Purchase, on_delete=models.CASCADE, related_name='expense_lines')
    category = models.ForeignKey(
        'expenses.ExpenseCategory', on_delete=models.PROTECT,
        related_name='purchase_expense_lines')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.category}: {self.amount}'
