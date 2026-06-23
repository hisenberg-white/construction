"""Dashboard and reports views (SRS FR-15).

The dashboard summarises the current company's position: KPI cards plus charts
for daily sales, daily profit and expense breakdown. All figures are scoped to
``request.tenant`` (a tenant user's own company, or the company a SaaS owner is
currently working in).
"""
import json
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from core import permissions as perms
from expenses.models import Expense
from inventory.models import MaterialItem, StockLedger, Vehicle
from ledger.models import Payment
from purchases.models import Purchase
from sales.models import SaleInvoice, SaleInvoiceLine


def _sum(qs, field):
    return qs.aggregate(s=Sum(field))['s'] or Decimal('0')


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if (request.user.is_authenticated and request.tenant is None
                and not request.user.is_saas_staff and not request.user.is_superuser):
            return redirect('accounts:no_tenant')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant
        context['no_company'] = tenant is None
        if tenant is None:
            # SaaS owner who hasn't picked a company yet.
            context.update({'cards': [], 'cards2': []})
            return context

        today = timezone.localdate()

        # Staff role: counts only, no monetary values.
        profile = getattr(self.request.user, 'profile', None)
        if profile is not None and profile.role == perms.STAFF:
            sales_count = SaleInvoice.objects.for_tenant(tenant).filter(
                invoice_date=today).exclude(status='cancelled').count()
            pur_count = Purchase.objects.for_tenant(tenant).filter(
                purchase_date=today).exclude(status='cancelled').count()
            exp_count = Expense.objects.for_tenant(tenant).filter(
                expense_date=today).exclude(status='cancelled').count()
            context['is_staff_role'] = True
            context['staff_counts'] = [
                {'label': "Today's Sales", 'value': sales_count,
                 'icon': 'bi-receipt', 'color': 'primary'},
                {'label': "Today's Purchases", 'value': pur_count,
                 'icon': 'bi-cart-plus', 'color': 'success'},
                {'label': "Today's Expenses", 'value': exp_count,
                 'icon': 'bi-wallet2', 'color': 'warning'},
            ]
            return context

        context['is_staff_role'] = False

        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        d0 = today - timedelta(days=29)

        invoices = SaleInvoice.objects.for_tenant(tenant).exclude(status='cancelled')
        purchases = Purchase.objects.for_tenant(tenant).exclude(status='cancelled')
        expenses = Expense.objects.for_tenant(tenant).exclude(status='cancelled')
        payments = Payment.objects.for_tenant(tenant).exclude(status='cancelled')

        sales_today = _sum(invoices.filter(invoice_date=today), 'total')
        sales_month = _sum(invoices.filter(invoice_date__gte=month_start), 'total')
        sales_year = _sum(invoices.filter(invoice_date__gte=year_start), 'total')
        collection_today = _sum(payments.filter(direction='in', payment_date=today), 'amount')
        credit_due = _sum(invoices.filter(due__gt=0), 'due')
        exp_month = _sum(expenses.filter(expense_date__gte=month_start), 'amount')
        exp_year = _sum(expenses.filter(expense_date__gte=year_start), 'amount')
        pur_month = _sum(purchases.filter(purchase_date__gte=month_start), 'total_cost')
        pur_year = _sum(purchases.filter(purchase_date__gte=year_start), 'total_cost')
        profit_month = sales_month - pur_month - exp_month
        profit_year = sales_year - pur_year - exp_year

        # Approximate stock value: net qty per material × its purchase rate.
        rates = {m.id: m.default_purchase_rate for m in MaterialItem.objects.for_tenant(tenant)}
        stock_value = Decimal('0')
        for row in (StockLedger.objects.for_tenant(tenant).values('material')
                    .annotate(i=Sum('qty_in'), o=Sum('qty_out'))):
            net = (row['i'] or 0) - (row['o'] or 0)
            stock_value += Decimal(net) * (rates.get(row['material']) or 0)

        cur = tenant.default_currency
        context['currency'] = cur
        context['cards'] = [
            {'label': "Today's Sales", 'value': sales_today, 'icon': 'bi-graph-up-arrow', 'color': 'primary'},
            {'label': "Today's Collection", 'value': collection_today, 'icon': 'bi-cash-stack', 'color': 'success'},
            {'label': 'Credit Due', 'value': credit_due, 'icon': 'bi-hourglass-split', 'color': 'warning'},
            {'label': 'Stock Value', 'value': stock_value, 'icon': 'bi-box-seam', 'color': 'info'},
        ]
        context['cards2'] = [
            {'label': 'Sales (This Month)', 'value': sales_month, 'icon': 'bi-calendar-month', 'color': 'primary'},
            {'label': 'Expenses (This Month)', 'value': exp_month, 'icon': 'bi-wallet2', 'color': 'danger'},
            {'label': 'Net Profit (This Month)', 'value': profit_month,
             'icon': 'bi-piggy-bank', 'color': 'success' if profit_month >= 0 else 'danger'},
            {'label': 'Net Profit (This Year)', 'value': profit_year,
             'icon': 'bi-trophy', 'color': 'success' if profit_year >= 0 else 'danger'},
        ]

        # --- Charts: last 30 days ---
        days = [d0 + timedelta(days=i) for i in range(30)]

        def _daymap(qs, date_field, value_field):
            return {r[date_field]: r['s'] for r in
                    qs.filter(**{date_field + '__gte': d0}).values(date_field).annotate(s=Sum(value_field))}

        sales_map = _daymap(invoices, 'invoice_date', 'total')
        pur_map = _daymap(purchases, 'purchase_date', 'total_cost')
        exp_map = _daymap(expenses, 'expense_date', 'amount')

        labels = [d.strftime('%b %d') for d in days]
        sales_series = [float(sales_map.get(d, 0) or 0) for d in days]
        profit_series = [float((sales_map.get(d, 0) or 0) - (pur_map.get(d, 0) or 0)
                               - (exp_map.get(d, 0) or 0)) for d in days]

        ecat = (expenses.filter(expense_date__gte=month_start).values('category__name')
                .annotate(s=Sum('amount')).order_by('-s')[:8])
        exp_labels = [r['category__name'] or '—' for r in ecat]
        exp_data = [float(r['s'] or 0) for r in ecat]

        context['chart_labels'] = json.dumps(labels)
        context['chart_sales'] = json.dumps(sales_series)
        context['chart_profit'] = json.dumps(profit_series)
        context['chart_exp_labels'] = json.dumps(exp_labels)
        context['chart_exp_data'] = json.dumps(exp_data)
        context['has_expense_breakdown'] = bool(exp_data)
        return context


class VehicleAnalyticsView(LoginRequiredMixin, TemplateView):
    """Per-vehicle revenue, cost and profit analytics (SRS FR-15)."""

    template_name = 'reports/vehicle_analytics.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if getattr(request, 'tenant', None) is None:
            if request.user.is_superuser or getattr(request.user, 'is_saas_staff', False):
                from django.contrib import messages as msg
                msg.info(request, 'Select a company from the top bar first.')
                return redirect('reports:dashboard')
            return redirect('accounts:no_tenant')
        from core.crud import PermissionRequiredMixin
        if not perms.has_perm(request.user, perms.REPORTS, 'r'):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = self.request.tenant

        vehicles = Vehicle.objects.for_tenant(tenant).filter(is_active=True)

        rows = []
        for v in vehicles:
            revenue = _sum(
                SaleInvoiceLine.objects.filter(invoice__tenant=tenant, vehicle=v),
                'amount'
            )
            purchase_cost = _sum(
                Purchase.objects.for_tenant(tenant).filter(vehicle=v).exclude(status='cancelled'),
                'total_cost'
            )
            expense_cost = _sum(
                Expense.objects.for_tenant(tenant).filter(vehicle=v).exclude(status='cancelled'),
                'amount'
            )
            profit = revenue - purchase_cost - expense_cost
            rows.append({
                'vehicle': v,
                'revenue': revenue,
                'purchase_cost': purchase_cost,
                'expense_cost': expense_cost,
                'profit': profit,
            })

        # Expense breakdown by category for vehicles.
        exp_by_cat = (
            Expense.objects.for_tenant(tenant)
            .filter(vehicle__isnull=False)
            .exclude(status='cancelled')
            .values('category__name')
            .annotate(s=Sum('amount'))
            .order_by('-s')[:10]
        )
        ebc_labels = [r['category__name'] or '—' for r in exp_by_cat]
        ebc_data = [float(r['s'] or 0) for r in exp_by_cat]

        veh_labels = [r['vehicle'].name for r in rows]
        veh_profit = [float(r['profit']) for r in rows]

        context['rows'] = rows
        context['chart_veh_labels'] = json.dumps(veh_labels)
        context['chart_veh_profit'] = json.dumps(veh_profit)
        context['chart_ebc_labels'] = json.dumps(ebc_labels)
        context['chart_ebc_data'] = json.dumps(ebc_data)
        context['has_ebc'] = bool(ebc_data)
        context['currency'] = tenant.default_currency
        return context
