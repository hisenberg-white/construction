"""Expense categories and expense entries (SRS FR-13)."""
from django.db import models

from core.constants import PaymentMethod
from core.models import CancellableModel, TenantOwnedModel


class ExpenseCategory(TenantOwnedModel):
    """Expense category: petrol, diesel, maintenance, salary, rent… (SRS FR-13)."""

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Expense categories'
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_expense_category_per_tenant'
            ),
        ]

    def __str__(self):
        return self.name


class Expense(TenantOwnedModel, CancellableModel):
    """An operating expense, optionally tied to a vehicle/employee/supplier (FR-13)."""

    depot = models.ForeignKey(
        'tenants.DepotLocation', on_delete=models.PROTECT,
        null=True, blank=True, related_name='expenses',
    )
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.PROTECT, related_name='expenses'
    )
    expense_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(
        max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    # Optional links so vehicle/employee/supplier costs are traceable (FR-13).
    vehicle = models.ForeignKey(
        'inventory.Vehicle', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='expenses',
    )
    employee = models.ForeignKey(
        'employees.Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='expenses',
    )
    supplier = models.ForeignKey(
        'parties.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='expenses',
    )
    notes = models.TextField(blank=True)
    reference_image = models.ImageField(
        upload_to='references/expenses/%Y/%m/', blank=True, null=True,
        help_text='Optional photo of the receipt / reference.')

    class Meta:
        ordering = ['-expense_date', '-id']
        indexes = [models.Index(fields=['tenant', 'depot', 'expense_date'])]

    def __str__(self):
        return f'{self.category} — {self.amount}'
