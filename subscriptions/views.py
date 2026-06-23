"""SaaS plans, subscriptions and usage views (SRS section 8, module 'saas')."""
from core.crud import (
    SaaSCreateView,
    SaaSDeleteView,
    SaaSDetailView,
    SaaSListView,
    SaaSUpdateView,
)

from .forms import SaaSPlanForm, SubscriptionForm
from .models import SaaSPlan, Subscription, SubscriptionUsage


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
                    'entry_count', 'amount_due']
    title = 'Subscription Usage'


class UsageDetailView(SaaSDetailView):
    model = SubscriptionUsage
    crud_basename = 'usage'
    list_display = ['tenant', 'period_start', 'period_end', 'invoice_count',
                    'entry_count', 'sms_count', 'storage_used_mb', 'amount_due']
