"""Ledger entries and payments (SRS FR-14, section 7).

Every financial transaction creates ledger entries with a running
``balance_after`` so customer/supplier/employee statements are auditable
(SRS 7.1). Use positive/negative entries consistently — never hand-edit a
balance (SRS 12.2).
"""
from django.db import models

from core.constants import LedgerAccountType, PartyType, PaymentMethod
from core.models import CancellableModel, TenantOwnedModel


class Payment(TenantOwnedModel, CancellableModel):
    """A payment received from a customer or paid to a supplier/employee (FR-08, FR-12)."""

    class Direction(models.TextChoices):
        IN = 'in', 'Received (money in)'
        OUT = 'out', 'Paid (money out)'

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.PROTECT,
        null=True, blank=True, related_name='payments',
    )
    party_type = models.CharField(max_length=12, choices=PartyType.choices)
    customer = models.ForeignKey(
        'parties.Customer', on_delete=models.PROTECT,
        null=True, blank=True, related_name='payments',
    )
    supplier = models.ForeignKey(
        'parties.Supplier', on_delete=models.PROTECT,
        null=True, blank=True, related_name='payments',
    )
    employee = models.ForeignKey(
        'employees.Employee', on_delete=models.PROTECT,
        null=True, blank=True, related_name='payments',
    )
    direction = models.CharField(max_length=3, choices=Direction.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    payment_date = models.DateField()
    reference_no = models.CharField(max_length=80, blank=True)
    notes = models.TextField(blank=True)
    reference_image = models.ImageField(
        upload_to='references/payments/%Y/%m/', blank=True, null=True,
        help_text='Optional photo of the voucher / reference.')
    # Source bill this payment was recorded against (sale_invoice / purchase).
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-payment_date', '-id']
        indexes = [models.Index(fields=['tenant', 'party_type', 'payment_date'])]

    def __str__(self):
        return f'Payment #{self.pk} — {self.amount} ({self.get_direction_display()})'


class LedgerEntry(TenantOwnedModel):
    """A single debit/credit line against a party account (SRS FR-14, 7.1).

    ``account_id`` references the row of the model identified by
    ``account_type`` (customer/supplier/employee/vehicle/company).
    """

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.PROTECT,
        null=True, blank=True, related_name='ledger_entries',
    )
    account_type = models.CharField(max_length=12, choices=LedgerAccountType.choices)
    account_id = models.PositiveBigIntegerField(
        null=True, blank=True,
        help_text='PK of the party account; empty for company-level accounts.',
    )
    entry_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    # Source document reference (invoice, payment, purchase…).
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-entry_date', '-id']
        verbose_name_plural = 'Ledger entries'
        indexes = [
            models.Index(fields=['tenant', 'account_type', 'account_id', 'entry_date']),
        ]

    def __str__(self):
        return f'{self.get_account_type_display()} #{self.account_id}: Dr {self.debit} / Cr {self.credit}'
