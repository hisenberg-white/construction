"""SubscriptionService — subscription status and entry-billing gate (SRS section 8).

Centralises the access-control decisions from SRS 8.2 / 10.6 and the per-entry
usage accounting from FR-18 (e.g. Rs. 3 per invoice/entry).
"""
import calendar
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import SubscriptionUsage


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
    @transaction.atomic
    def record_entry_usage(*, tenant, kind='entry', count=1):
        """Add ``count`` billable entries to the tenant's current-month usage and
        accrue the per-entry charge (SRS FR-18).

        Returns the updated :class:`SubscriptionUsage` row for the period.
        """
        today = timezone.now().date()
        period_start = today.replace(day=1)
        period_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
        price = SubscriptionService.per_entry_price(tenant)

        usage, _ = SubscriptionUsage.objects.get_or_create(
            tenant=tenant, period_start=period_start, period_end=period_end,
            defaults={'invoice_count': 0, 'entry_count': 0, 'amount_due': Decimal('0')},
        )
        if kind == 'invoice':
            usage.invoice_count += count
        usage.entry_count += count
        usage.amount_due = (usage.amount_due or Decimal('0')) + price * count
        usage.save(update_fields=['invoice_count', 'entry_count', 'amount_due', 'updated_at'])
        return usage

    @staticmethod
    @transaction.atomic
    def refresh_status(tenant):
        """Recompute subscription_status from dates/grace period (SRS 8.2, 10.6)."""
        raise NotImplementedError('SubscriptionService.refresh_status — roadmap Phase 5')
