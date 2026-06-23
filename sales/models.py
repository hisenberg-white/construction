"""Sale invoices, invoice lines and delivery/share logs (SRS FR-08, FR-16)."""
from decimal import Decimal

from django.db import models

from core.constants import PaymentStatus
from core.models import CancellableModel, TenantOwnedModel


class SaleInvoice(TenantOwnedModel, CancellableModel):
    """A sale/invoice to a customer (SRS FR-08).

    Invoice numbers are unique per tenant with a configurable prefix
    (SRS 12.2). Invoices are voided/cancelled, never hard-deleted (FR-17).
    """

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.PROTECT, related_name='invoices'
    )
    customer = models.ForeignKey(
        'parties.Customer', on_delete=models.PROTECT, related_name='invoices'
    )
    invoice_no = models.CharField(max_length=60)
    invoice_date = models.DateField()

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    additional_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    due = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID
    )
    notes = models.TextField(blank=True)
    reference_image = models.ImageField(
        upload_to='references/invoices/%Y/%m/', blank=True, null=True,
        help_text='Optional photo of the bill / reference.')

    class Meta:
        ordering = ['-invoice_date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'invoice_no'], name='unique_invoice_no_per_tenant'
            ),
        ]
        indexes = [
            models.Index(fields=['tenant', 'depot', 'invoice_date']),
            models.Index(fields=['tenant', 'customer']),
        ]

    def recompute_totals(self, save=True):
        """Recalculate subtotal/total/due/payment_status from the lines (SRS FR-08)."""
        agg = self.lines.aggregate(s=models.Sum('amount'))
        self.subtotal = agg['s'] or Decimal('0')
        self.total = (self.subtotal + (self.additional_charges or 0)
                      - (self.discount or 0) + (self.tax or 0))
        self.due = self.total - (self.paid or 0)
        paid = self.paid or Decimal('0')
        if paid <= 0:
            self.payment_status = PaymentStatus.UNPAID
        elif paid >= self.total:
            self.payment_status = PaymentStatus.PAID
        else:
            self.payment_status = PaymentStatus.PARTIAL
        if save:
            super().save(update_fields=['subtotal', 'total', 'due', 'payment_status',
                                        'updated_at'])

    def __str__(self):
        return self.invoice_no


class SaleInvoiceLine(models.Model):
    """A single material/service line on an invoice (SRS FR-08, appendix 16)."""

    invoice = models.ForeignKey(
        SaleInvoice, on_delete=models.CASCADE, related_name='lines'
    )
    material = models.ForeignKey(
        'inventory.MaterialItem', on_delete=models.PROTECT,
        null=True, blank=True, related_name='invoice_lines',
    )
    service = models.ForeignKey(
        'inventory.ServiceItem', on_delete=models.PROTECT,
        null=True, blank=True, related_name='invoice_lines',
    )
    vehicle_type = models.ForeignKey(
        'inventory.VehicleType', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoice_lines',
    )
    vehicle = models.ForeignKey(
        'inventory.Vehicle', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='invoice_lines',
    )
    description = models.CharField(max_length=255, blank=True)
    qty = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit = models.CharField(max_length=40, blank=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Captured cost basis for profit calculation (SRS 7.1, 7.2).
    cost_reference = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.amount = (self.qty or 0) * (self.rate or 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.invoice.invoice_no} line — {self.material or self.service}'


class DeliveryLog(TenantOwnedModel):
    """Record of how/when an invoice was shared (SRS FR-16)."""

    class Method(models.TextChoices):
        PRINT = 'print', 'Print'
        EMAIL = 'email', 'Email'
        SMS = 'sms', 'SMS'
        WHATSAPP = 'whatsapp', 'WhatsApp'

    class DeliveryStatus(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    invoice = models.ForeignKey(
        SaleInvoice, on_delete=models.CASCADE, related_name='delivery_logs'
    )
    method = models.CharField(max_length=10, choices=Method.choices)
    recipient = models.CharField(max_length=200, blank=True)
    delivery_status = models.CharField(
        max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.QUEUED
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.invoice.invoice_no} via {self.get_method_display()}'
