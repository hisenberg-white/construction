from django.contrib import admin

from .models import SaaSPlan, Subscription, SubscriptionUsage


@admin.register(SaaSPlan)
class SaaSPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'billing_cycle', 'base_price', 'per_entry_price',
                    'entry_limit', 'is_active')
    list_filter = ('billing_cycle', 'is_active')
    search_fields = ('name',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'plan', 'start_date', 'end_date', 'is_current')
    list_filter = ('is_current', 'plan')
    search_fields = ('tenant__name',)
    date_hierarchy = 'start_date'


@admin.register(SubscriptionUsage)
class SubscriptionUsageAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'period_start', 'period_end', 'invoice_count',
                    'entry_count', 'amount_due')
    list_filter = ('tenant',)
    date_hierarchy = 'period_start'
