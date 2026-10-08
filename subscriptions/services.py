"""SubscriptionService — subscription status and entry-billing gate (SRS section 8).

Centralises the access-control decisions from SRS 8.2 / 10.6 and the per-entry
usage accounting from FR-18 (e.g. Rs. 3 per invoice/entry).
"""
import calendar
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import SubscriptionUsage, UsageEntry


class SubscriptionService:
    @staticmethod
    def can_create_entry(tenant):
        """Whether ``tenant`` may create a new billable entry right now (SRS 8.2)."""
        return tenant.can_create_entries

    @staticmethod
    def per_entry_price(tenant):
        """Resolve the price charged per billable entry (FR-18).

        A current subscription's ``custom_per_entry_price`` wins; otherwise the
        active plan's ``per_entry_price``; otherwise zero.
        """
        sub = (tenant.subscriptions.filter(is_current=True)
               .select_related('plan').first())
        if sub and sub.custom_per_entry_price is not None:
            return sub.custom_per_entry_price
        if sub and sub.plan_id:
            return sub.plan.per_entry_price
        if tenant.current_plan_id:
            return tenant.current_plan.per_entry_price
        return Decimal('0')

    @staticmethod
    def _current_usage(tenant):
        today = timezone.now().date()
        period_start = today.replace(day=1)
        period_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        usage, _ = SubscriptionUsage.objects.get_or_create(
            tenant=tenant, period_start=period_start, period_end=period_end,
            defaults={'invoice_count': 0, 'entry_count': 0, 'amount_due': Decimal('0')},
        )
        return usage

    @staticmethod
    def _log_entry(usage, *, kind, obj, description, price, actor):
        UsageEntry.objects.create(
            usage=usage, tenant=usage.tenant, kind=kind,
            reference_type=_reference_type(obj), reference_id=getattr(obj, 'pk', None),
            description=description or (str(obj) if obj is not None else ''),
            price=price, created_by=actor if getattr(actor, 'is_authenticated', False) else None)

    @staticmethod
    @transaction.atomic
    def record_entry_usage(*, tenant, kind='entry', count=1, obj=None, actor=None, description=''):
        """Add ``count`` billable entries to the tenant's current-month usage,
        accrue the per-entry charge (SRS FR-18) and log which document caused it.

        Returns the updated :class:`SubscriptionUsage` row for the period.
        """
        usage = SubscriptionService._current_usage(tenant)
        price = SubscriptionService.per_entry_price(tenant)
        if kind == 'invoice':
            usage.invoice_count += count
        usage.entry_count += count
        usage.amount_due = (usage.amount_due or Decimal('0')) + price * count
        usage.save(update_fields=['invoice_count', 'entry_count', 'amount_due', 'updated_at'])
        for _ in range(count):
            SubscriptionService._log_entry(usage, kind=kind, obj=obj, description=description,
                                           price=price, actor=actor)
        return usage

    @staticmethod
    @transaction.atomic
    def record_sms_usage(*, tenant, count=1, obj=None, actor=None, description=''):
        """Count SMS sent this month in the tenant's usage row (SRS FR-18).
        SMS are listed in the usage detail but not charged per entry."""
        usage = SubscriptionService._current_usage(tenant)
        usage.sms_count += count
        usage.save(update_fields=['sms_count', 'updated_at'])
        for _ in range(count):
            SubscriptionService._log_entry(usage, kind='sms', obj=obj, description=description,
                                           price=Decimal('0'), actor=actor)
        return usage

    @staticmethod
    @transaction.atomic
    def refresh_status(tenant):
        """Recompute subscription_status from dates/grace period (SRS 8.2, 10.6)."""
        raise NotImplementedError('SubscriptionService.refresh_status — roadmap Phase 5')


def _reference_type(obj):
    """Same reference names the ledger uses ('sale_invoice', 'purchase')."""
    if obj is None:
        return ''
    return {'SaleInvoice': 'sale_invoice', 'Purchase': 'purchase'}.get(
        type(obj).__name__, type(obj).__name__.lower())
