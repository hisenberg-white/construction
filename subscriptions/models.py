"""SaaS plans, subscriptions and usage/entry billing (SRS section 8, FR-18)."""
from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimeStampedModel


class SaaSPlan(TimeStampedModel):
    """A subscription plan offered by the SaaS owner (SRS FR-18)."""

    class BillingCycle(models.TextChoices):
        TRIAL = 'trial', 'Trial'
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'
        CUSTOM = 'custom', 'Custom'
        PAY_PER_ENTRY = 'pay_per_entry', 'Pay Per Entry'
        HYBRID = 'hybrid', 'Hybrid'

    name = models.CharField(max_length=100)
    billing_cycle = models.CharField(
        max_length=20, choices=BillingCycle.choices, default=BillingCycle.MONTHLY
    )
    base_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # e.g. Rs. 3 per invoice/transaction (SRS 1.3, FR-18).
    per_entry_price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    user_limit = models.PositiveIntegerField(null=True, blank=True)
    depot_limit = models.PositiveIntegerField(null=True, blank=True)
    entry_limit = models.PositiveIntegerField(null=True, blank=True)
    storage_limit_mb = models.PositiveIntegerField(null=True, blank=True)
    features_json = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['base_price']

    def __str__(self):
        return self.name


class Subscription(TimeStampedModel):
    """A tenant's subscription period to a plan (SRS 8.2)."""

    tenant = models.ForeignKey(
        'tenants.TenantCompany',
        on_delete=models.CASCADE,
        related_name='subscriptions',
    )
    plan = models.ForeignKey(
        SaaSPlan, on_delete=models.PROTECT, related_name='subscriptions'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    grace_days = models.PositiveIntegerField(default=0)
    renewal_date = models.DateField(null=True, blank=True)
    custom_per_entry_price = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.tenant} → {self.plan} ({self.start_date} to {self.end_date})'


class SubscriptionUsage(TimeStampedModel):
    """Per-period billable usage counters for a tenant (SRS FR-18, 8.1)."""

    tenant = models.ForeignKey(
        'tenants.TenantCompany',
        on_delete=models.CASCADE,
        related_name='usage_records',
    )
    period_start = models.DateField()
    period_end = models.DateField()
    invoice_count = models.PositiveIntegerField(default=0)
    entry_count = models.PositiveIntegerField(default=0)
    sms_count = models.PositiveIntegerField(default=0)
    storage_used_mb = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ['-period_start']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'period_start', 'period_end'],
                name='unique_usage_period_per_tenant',
            ),
        ]

    def __str__(self):
        return f'{self.tenant} usage {self.period_start}–{self.period_end}'


class UsageEntry(models.Model):
    """One billable event behind a :class:`SubscriptionUsage` period — which
    invoice / purchase / SMS it was and what it was charged (SRS FR-18)."""

    class Kind(models.TextChoices):
        INVOICE = 'invoice', 'Sales Invoice'
        PURCHASE = 'purchase', 'Purchase'
        SMS = 'sms', 'SMS'
        ENTRY = 'entry', 'Other entry'

    usage = models.ForeignKey(SubscriptionUsage, on_delete=models.CASCADE, related_name='entries')
    tenant = models.ForeignKey('tenants.TenantCompany', on_delete=models.CASCADE,
                               related_name='usage_entries')
    kind = models.CharField(max_length=10, choices=Kind.choices)
    # The document that caused the charge (sale_invoice / purchase + its pk).
    reference_type = models.CharField(max_length=40, blank=True)
    reference_id = models.PositiveBigIntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    # True for rows rebuilt from documents for periods recorded before
    # per-entry tracking existed (price is the period average).
    reconstructed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['usage', 'kind'])]

    def __str__(self):
        return f'{self.get_kind_display()} {self.description} ({self.price})'
