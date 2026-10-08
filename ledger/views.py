"""Payment CRUD and ledger viewing (SRS FR-08, FR-12, FR-14, module 'payments_ledger').

Recording a payment posts a ledger entry against the party account; cancelling
reverses it (SRS 7.1, FR-17).
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from core import permissions
from core.pagination import paginate
from core.constants import COMPANY_ACCOUNTS, LedgerAccountType, PartyType
from core.crud import (
    CrudCancelView,
    CrudCreateView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
    PermissionRequiredMixin,
    TenantRequiredMixin,
)
from employees.models import Employee
from inventory.models import Vehicle
from parties.models import Customer, Supplier

from .forms import PaymentForm
from .models import LedgerEntry, Payment
from .services import LedgerService

MODULE = permissions.PAYMENTS_LEDGER


def _account(payment):
    if payment.party_type == 'customer' and payment.customer_id:
        return 'customer', payment.customer_id
    if payment.party_type == 'supplier' and payment.supplier_id:
        return 'supplier', payment.supplier_id
    if payment.party_type == 'employee' and payment.employee_id:
        return 'employee', payment.employee_id
    return payment.party_type, None


def _post_payment(payment, actor, *, reverse=False):
    account_type, account_id = _account(payment)
    if not account_id:
        return
    money_in = payment.direction == Payment.Direction.IN
    if reverse:
        money_in = not money_in
    debit = 0 if money_in else payment.amount
    credit = payment.amount if money_in else 0
    LedgerService.post(
        tenant=payment.tenant, account_type=account_type, account_id=account_id,
        entry_date=payment.payment_date,
        description=('Reversal of ' if reverse else '') + f'payment #{payment.pk}',
        debit=debit, credit=credit,
        reference_type='payment', reference_id=payment.pk,
        depot=payment.depot, actor=actor,
    )


class PaymentListView(CrudListView):
    model = Payment
    permission_module = MODULE
    crud_basename = 'payment'
    delete_action = 'cancel'
    list_display = ['payment_date', 'party_type', 'direction', 'amount',
                    'method', 'reference_no', 'status']


class PaymentDetailView(CrudDetailView):
    model = Payment
    permission_module = MODULE
    crud_basename = 'payment'
    delete_action = 'cancel'
    list_display = ['payment_date', 'depot', 'party_type', 'customer', 'supplier',
                    'employee', 'direction', 'amount', 'method', 'reference_no',
                    'status', 'notes']


class PaymentCreateView(CrudCreateView):
    model = Payment
    permission_module = MODULE
    crud_basename = 'payment'
    form_class = PaymentForm
    template_name = 'ledger/payment_form.html'

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        _post_payment(self.object, self.request.user)
        return response


class PaymentUpdateView(CrudUpdateView):
    model = Payment
    permission_module = MODULE
    crud_basename = 'payment'
    form_class = PaymentForm
    template_name = 'ledger/payment_form.html'


class PaymentCancelView(CrudCancelView):
    model = Payment
    permission_module = MODULE
    crud_basename = 'payment'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.is_cancelled:
            _post_payment(obj, request.user, reverse=True)
        return super().post(request, *args, **kwargs)


# --- Ledger entries (read-only) ----------------------------------------------
# Per-party ledger accounts and the model whose name labels them.
PARTY_ACCOUNT_MODELS = {
    'customer': Customer,
    'supplier': Supplier,
    'employee': Employee,
    'vehicle': Vehicle,
}


def _attach_account_names(entries):
    """Set ``entry.account_name`` — e.g. "Ram sharma (Customer Account)" for
    per-party rows, or the plain account label ("Sales Account") otherwise.
    One query per party type on the page."""
    entries = list(entries)
    names = {}
    for acc_type, model in PARTY_ACCOUNT_MODELS.items():
        ids = {e.account_id for e in entries if e.account_type == acc_type and e.account_id}
        if ids:
            names[acc_type] = dict(model.objects.filter(pk__in=ids).values_list('pk', 'name'))
    for e in entries:
        label = e.get_account_type_display()
        name = names.get(e.account_type, {}).get(e.account_id)
        if name:
            suffix = 'Account' if label.endswith('Account') else f'{label} Account'
            e.account_name = f'{name} ({suffix})'
        elif e.account_id:
            e.account_name = f'{label} #{e.account_id}'
        else:
            e.account_name = label


def _net(qs):
    """Debit − credit over ``qs`` (positive = they owe you)."""
    agg = qs.aggregate(d=Sum('debit'), c=Sum('credit'))
    return (agg['d'] or Decimal('0')) - (agg['c'] or Decimal('0'))


def balance_status(name, amount):
    """Plain-language reading of a party balance: (key, sentence)."""
    if amount > 0:
        return 'receive', f'{name} owes you'
    if amount < 0:
        return 'pay', f'You owe {name}'
    return 'settled', 'Settled — nothing due'


def outstanding_balances(tenant, as_of):
    """Every customer / supplier / employee / vehicle account with a non-zero
    balance on ``as_of``, biggest first, plus totals to receive and to pay."""
    rows = (LedgerEntry.objects.for_tenant(tenant)
            .filter(account_type__in=PARTY_ACCOUNT_MODELS, account_id__isnull=False,
                    entry_date__lte=as_of)
            .values('account_type', 'account_id')
            .annotate(d=Sum('debit'), c=Sum('credit')))
    balances = [(r['account_type'], r['account_id'], (r['d'] or 0) - (r['c'] or 0)) for r in rows]
    balances = [b for b in balances if b[2]]
    names = {}
    for acc_type, model in PARTY_ACCOUNT_MODELS.items():
        ids = {b[1] for b in balances if b[0] == acc_type}
        if ids:
            names[acc_type] = dict(model.objects.filter(pk__in=ids).values_list('pk', 'name'))
    labels = dict(LedgerAccountType.choices)
    out = []
    for acc_type, acc_id, amount in sorted(balances, key=lambda b: -abs(b[2])):
        out.append({
            'name': names.get(acc_type, {}).get(acc_id, f'#{acc_id}'),
            'type_label': labels.get(acc_type, acc_type),
            'account': f'{acc_type}:{acc_id}',
            'receive': amount if amount > 0 else 0,
            'pay': -amount if amount < 0 else 0,
        })
    return {
        'rows': out,
        'total_receive': sum(r['receive'] for r in out),
        'total_pay': sum(r['pay'] for r in out),
    }


class LedgerPaperView(TenantRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Account ledger styled like a ledger book (SRS FR-14).

    * A single ``account`` picker covers the company books (Sales / Purchase /
      Expense / Cash), a Profit & Loss summary, and every individual customer,
      supplier and employee account (credit customers each have their own).
    * Date filter defaults to the last month.
    * When a single account is chosen, the balance carried forward from before
      the range is shown as the Opening Balance — so each fiscal year opens with
      the previous year's closing balance.
    """

    permission_module = MODULE
    permission_action = 'r'
    template_name = 'ledger/ledger.html'

    def _parse_date(self, key, default):
        try:
            return timezone.datetime.strptime(self.request.GET.get(key, ''), '%Y-%m-%d').date()
        except ValueError:
            return default

    def _base_qs(self):
        qs = LedgerEntry.objects.all()
        if self.request.tenant is not None:
            qs = qs.for_tenant(self.request.tenant)
        return qs

    def _account_options(self):
        tenant = self.request.tenant
        opts = [
            ('', 'All accounts'),
            ('sales', 'Sales Account'),
            ('purchase', 'Purchase Account'),
            ('expense', 'Expense Account'),
            ('cash', 'Cash / Bank'),
            ('pl', 'Profit & Loss (summary)'),
        ]
        if tenant is not None:
            for c in Customer.objects.for_tenant(tenant).order_by('name'):
                opts.append((f'customer:{c.pk}', f'Customer: {c.name}'))
            for s in Supplier.objects.for_tenant(tenant).order_by('name'):
                opts.append((f'supplier:{s.pk}', f'Supplier: {s.name}'))
            for e in Employee.objects.for_tenant(tenant).order_by('name'):
                opts.append((f'employee:{e.pk}', f'Employee: {e.name}'))
        return opts

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        date_from = self._parse_date('from', today - timedelta(days=30))
        date_to = self._parse_date('to', today)
        account = self.request.GET.get('account', '')
        options = self._account_options()
        account_label = dict(options).get(account, 'All accounts')

        context.update({
            'date_from': date_from, 'date_to': date_to,
            'account': account, 'account_options': options,
            'account_label': account_label,
            'company': self.request.tenant,
        })

        # Profit & Loss summary (Sales − Purchase − Expense) for the period.
        if account == 'pl':
            def net(acc, positive='credit'):
                agg = (self._base_qs().filter(account_type=acc,
                       entry_date__gte=date_from, entry_date__lte=date_to)
                       .aggregate(d=Sum('debit'), c=Sum('credit')))
                d, c = agg['d'] or 0, agg['c'] or 0
                return (c - d) if positive == 'credit' else (d - c)
            sales = net('sales', 'credit')
            purchase = net('purchase', 'debit')
            expense = net('expense', 'debit')
            context.update({
                'pl': True,
                'pl_sales': sales, 'pl_purchase': purchase, 'pl_expense': expense,
                'pl_net': sales - purchase - expense,
            })
            return context

        # Resolve the selected account into (type, id).
        acc_type, acc_id = '', None
        if ':' in account:
            acc_type, raw = account.split(':', 1)
            acc_id = int(raw) if raw.isdigit() else None
        elif account in COMPANY_ACCOUNTS:
            acc_type = account

        qs = self._base_qs()
        single = bool(acc_type)
        if single:
            qs = qs.filter(account_type=acc_type)
            if acc_type in COMPANY_ACCOUNTS:
                qs = qs.filter(account_id__isnull=True)
            else:
                qs = qs.filter(account_id=acc_id)

        # Opening balance carried forward from before the range (yearly reset).
        # Summed from the entries rather than read off a stored running balance,
        # so back-dated payments / corrections can't skew it.
        opening = _net(qs.filter(entry_date__lt=date_from)) if single else None

        rows = qs.filter(entry_date__gte=date_from, entry_date__lte=date_to).order_by('entry_date', 'id')
        totals = rows.aggregate(debit=Sum('debit'), credit=Sum('credit'))
        total_debit, total_credit = totals['debit'] or 0, totals['credit'] or 0
        if single:
            closing = opening + total_debit - total_credit
            summary = {'opening': opening, 'debit': total_debit, 'credit': total_credit,
                       'closing': closing, 'party': acc_type in PARTY_ACCOUNT_MODELS}
            if summary['party']:
                name = account_label.split(': ', 1)[-1]
                summary['status'], summary['sentence'] = balance_status(name, closing)
                summary['amount'] = abs(closing)
            context['summary'] = summary
        else:
            context['outstanding'] = outstanding_balances(self.request.tenant, date_to)
        page_obj, is_paginated = paginate(self.request, rows)
        _attach_account_names(page_obj.object_list)
        brought_forward = page_obj.number > 1
        if single:
            # Running balance computed from the entries (opening + Dr − Cr),
            # carried over from earlier pages when paginated.
            running = opening + sum(
                (d - c) for d, c in rows[:page_obj.start_index() - 1].values_list('debit', 'credit'))
            if brought_forward:
                opening = running
            for e in page_obj.object_list:
                running += e.debit - e.credit
                e.running_balance = running
        context.update({
            'entries': page_obj.object_list,
            'page_obj': page_obj, 'is_paginated': is_paginated,
            'brought_forward': brought_forward,
            'opening_balance': opening,
            'single_account': single,
            'total_debit': total_debit,
            'total_credit': total_credit,
        })
        return context


class LedgerEntryDetailView(CrudDetailView):
    model = LedgerEntry
    permission_module = MODULE
    crud_basename = 'ledgerentry'
    list_display = ['entry_date', 'depot', 'account_type', 'account_id', 'description',
                    'debit', 'credit', 'balance_after', 'reference_type', 'reference_id']
