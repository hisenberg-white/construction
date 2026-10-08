"""SaaS plans, subscriptions and usage views (SRS section 8, module 'saas')."""
from core.crud import (
    SaaSCreateView,
    SaaSDeleteView,
    SaaSDetailView,
    SaaSListView,
    SaaSUpdateView,
)

from django.db.models import Count, Sum

from core.pagination import paginate

from .forms import SaaSPlanForm, SubscriptionForm
from .models import SaaSPlan, Subscription, SubscriptionUsage, UsageEntry


# --- Plans -------------------------------------------------------------------
class PlanListView(SaaSListView):
    model = SaaSPlan
    crud_basename = 'plan'
    list_display = ['name', 'billing_cycle', 'base_price', 'per_entry_price',
                    'entry_limit', 'is_active']
    title = 'SaaS Plans'


class PlanDetailView(SaaSDetailView):
    model = SaaSPlan
    crud_basename = 'plan'
    list_display = ['name', 'billing_cycle', 'base_price', 'per_entry_price',
                    'user_limit', 'depot_limit', 'entry_limit',
                    'storage_limit_mb', 'is_active']


class PlanCreateView(SaaSCreateView):
    model = SaaSPlan
    crud_basename = 'plan'
    form_class = SaaSPlanForm


class PlanUpdateView(SaaSUpdateView):
    model = SaaSPlan
    crud_basename = 'plan'
    form_class = SaaSPlanForm


class PlanDeleteView(SaaSDeleteView):
    model = SaaSPlan
    crud_basename = 'plan'
    list_display = ['name']


# --- Subscriptions -----------------------------------------------------------
class SubscriptionListView(SaaSListView):
    model = Subscription
    crud_basename = 'subscription'
    list_display = ['tenant', 'plan', 'start_date', 'end_date', 'is_current']
    title = 'Subscriptions'


class SubscriptionDetailView(SaaSDetailView):
    model = Subscription
    crud_basename = 'subscription'
    list_display = ['tenant', 'plan', 'start_date', 'end_date', 'grace_days',
                    'renewal_date', 'custom_per_entry_price', 'is_current']


class SubscriptionCreateView(SaaSCreateView):
    model = Subscription
    crud_basename = 'subscription'
    form_class = SubscriptionForm


class SubscriptionUpdateView(SaaSUpdateView):
    model = Subscription
    crud_basename = 'subscription'
    form_class = SubscriptionForm


class SubscriptionDeleteView(SaaSDeleteView):
    model = Subscription
    crud_basename = 'subscription'
    list_display = ['tenant', 'plan']


# --- Usage (read-only) -------------------------------------------------------
class UsageListView(SaaSListView):
    model = SubscriptionUsage
    crud_basename = 'usage'
    list_display = ['tenant', 'period_start', 'period_end', 'invoice_count',
                    'entry_count', 'sms_count', 'amount_due']
    title = 'Subscription Usage'

    def get_queryset(self):
        return super().get_queryset().select_related('tenant')


class UsageDetailView(SaaSDetailView):
    """One billing period: totals plus every entry that made them up."""

    model = SubscriptionUsage
    crud_basename = 'usage'
    template_name = 'subscriptions/usage_detail.html'
    list_display = ['tenant', 'period_start', 'period_end', 'invoice_count',
                    'entry_count', 'sms_count', 'storage_used_mb', 'amount_due']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usage = self.object
        entries = usage.entries.select_related('created_by')
        breakdown = {r['kind']: r for r in entries.values('kind')
                     .annotate(n=Count('id'), amount=Sum('price')).order_by()}
        kinds = [(value, label, breakdown.get(value, {}).get('n', 0),
                  breakdown.get(value, {}).get('amount') or 0)
                 for value, label in UsageEntry.Kind.choices if value in breakdown]

        kind = self.request.GET.get('kind', '')
        if kind in breakdown:
            entries = entries.filter(kind=kind)
        page_obj, is_paginated = paginate(self.request, entries, per_page=25)
        _mark_cancelled(page_obj.object_list)

        context.update({
            'usage': usage,
            'kinds': kinds, 'kind': kind,
            'entries': page_obj.object_list,
            'page_obj': page_obj, 'is_paginated': is_paginated,
            'entries_total': sum(k[3] for k in kinds),
            'has_reconstructed': usage.entries.filter(reconstructed=True).exists(),
            'currency': usage.tenant.default_currency,
        })
        return context


def _mark_cancelled(entries):
    """Flag entries whose invoice / purchase was cancelled after being billed."""
    from purchases.models import Purchase
    from sales.models import SaleInvoice
    entries = list(entries)
    for ref_type, model in (('sale_invoice', SaleInvoice), ('purchase', Purchase)):
        ids = {e.reference_id for e in entries
               if e.reference_type == ref_type and e.kind != 'sms' and e.reference_id}
        cancelled = set(model.objects.filter(pk__in=ids, status='cancelled').values_list('pk', flat=True)) if ids else set()
        for e in entries:
            if e.reference_type == ref_type and e.reference_id in cancelled and e.kind != 'sms':
                e.doc_cancelled = True
