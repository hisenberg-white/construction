"""Customer and supplier master data (SRS FR-06)."""
from django.db import models

from core.models import TenantOwnedModel


class Customer(TenantOwnedModel):
    """A buyer of materials/services, with a credit account (SRS FR-06)."""

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['tenant', 'name'])]

    def __str__(self):
        return self.name


class Supplier(TenantOwnedModel):
    """A vendor: material supplier, transport, fuel or maintenance (SRS FR-06)."""

    class SupplierType(models.TextChoices):
        MATERIAL = 'material', 'Material Supplier'
        TRANSPORT = 'transport', 'Transport Vendor'
        FUEL = 'fuel', 'Fuel Vendor'
        MAINTENANCE = 'maintenance', 'Maintenance Vendor'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    supplier_type = models.CharField(
        max_length=20, choices=SupplierType.choices, default=SupplierType.MATERIAL
    )
    opening_balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['tenant', 'name'])]

    def __str__(self):
        return self.name
