"""Purchase and trip CRUD (SRS FR-07, FR-10, module 'purchases').

Creating an active purchase posts stock-in (StockService) and, when bought on
credit, a supplier payable (LedgerService). Cancelling reverses both — financial
records are never hard-deleted (SRS FR-17).
"""
from django.contrib import messages
from django.core import signing
from django.db import transaction
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView

from audit.services import log_action
from core.qr import bill_pk, bill_token, qr_data_uri

from core import permissions
from core.crud import (
    CrudCancelView,
    CrudContextMixin,
    CrudCreateView,
    CrudDetailView,
    CrudListView,
    CrudUpdateView,
    PermissionRequiredMixin,
    TenantRequiredMixin,
)
from core.constants import PaymentStatus
from core.pdf import render_pdf_bytes
from inventory.models import StockLedger
from inventory.services import StockService, vehicle_capacity_json
from ledger.forms import RecordPaymentForm
from ledger.models import Payment
from ledger.services import LedgerService
from subscriptions.services import SubscriptionService

from .forms import PurchaseExpenseFormSet, PurchaseForm, TripForm
from .models import Purchase, Trip

MODULE = permissions.PURCHASES


def _payment_status(paid, total):
    if paid <= 0:
        return PaymentStatus.UNPAID
    if paid >= total:
        return PaymentStatus.PAID
    return PaymentStatus.PARTIAL


def _purchase_for_request(request, pk):
    qs = Purchase.objects.all()
    if request.tenant is not None:
        qs = qs.for_tenant(request.tenant)
    return get_object_or_404(
        qs.select_related('supplier', 'material', 'vehicle', 'depot', 'tenant'), pk=pk)


PURCHASE_SALT = 'purchase-public'


def _purchase_qr(request, purchase):
    token = bill_token(purchase.pk, PURCHASE_SALT)
    url = request.build_absolute_uri(reverse('purchases:purchase_public', args=[token]))
    return qr_data_uri(url)


class PurchasePublicView(View):
    """Read-only branded purchase opened by scanning the QR (no login; access
    is via the unguessable signed token)."""

    def get(self, request, token):
        try:
            pk = bill_pk(token, PURCHASE_SALT)
        except signing.BadSignature:
            raise Http404
        purchase = get_object_or_404(
            Purchase.objects.select_related('supplier', 'material', 'vehicle', 'depot', 'tenant'),
            pk=pk)
        company = purchase.tenant
        return render(request, 'purchases/purchase_pdf.html', {
            'purchase': purchase, 'company': company,
            'logo_path': company.logo.url if company.logo else None,
        })


def _post_purchase_effects(purchase, actor, *, reverse=False):
    """Post (or reverse) the stock and ledger impact of a purchase."""
    if purchase.material_id and purchase.material.stock_enabled:
        txn = (StockLedger.TransactionType.ADJUST_OUT if reverse
               else StockLedger.TransactionType.PURCHASE)
        StockService.record_movement(
            tenant=purchase.tenant, depot=purchase.depot, material=purchase.material,
            transaction_type=txn, qty=purchase.qty,
            reference_type='purchase', reference_id=purchase.pk,
            note=('Reversal of ' if reverse else '') + f'purchase #{purchase.pk}',
            actor=actor,
        )
    due = purchase.due_amount
    if due and due > 0 and purchase.supplier_id:
        # Supplier payable (per-supplier ledger).
        LedgerService.post(
            tenant=purchase.tenant, account_type='supplier',
            account_id=purchase.supplier_id, entry_date=purchase.purchase_date,
            description=('Reversal of ' if reverse else '') + f'purchase #{purchase.pk}',
            debit=due if reverse else 0, credit=0 if reverse else due,
            reference_type='purchase', reference_id=purchase.pk,
            depot=purchase.depot, actor=actor,
        )
    # Company Purchase account — cost of goods purchased (SRS FR-14).
    total = purchase.total_cost or 0
    if total > 0:
        LedgerService.post(
            tenant=purchase.tenant, account_type='purchase', account_id=None,
            entry_date=purchase.purchase_date,
            description=('Reversal of ' if reverse else '') + f'purchase #{purchase.pk}',
            debit=0 if reverse else total, credit=total if reverse else 0,
            reference_type='purchase', reference_id=purchase.pk,
            depot=purchase.depot, actor=actor,
        )


class PurchaseListView(CrudListView):
    model = Purchase
    permission_module = MODULE
    crud_basename = 'purchase'
    delete_action = 'cancel'
    list_display = ['purchase_date', 'supplier', 'material', 'qty', 'rate',
                    'total_cost', 'payment_status', 'status']

    def get_queryset(self):
        return super().get_queryset().select_related('supplier', 'material', 'depot')


class PurchaseDetailView(CrudDetailView):
    model = Purchase
    permission_module = MODULE
    crud_basename = 'purchase'
    delete_action = 'cancel'
    template_name = 'purchases/purchase_detail.html'
    list_display = ['purchase_date', 'depot', 'supplier', 'material', 'vehicle',
                    'reference_no', 'qty', 'rate', 'material_cost', 'transport_cost',
                    'unloading_cost', 'other_cost', 'total_cost', 'paid_amount',
                    'payment_status', 'status', 'notes']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['record_payment_form'] = RecordPaymentForm()
        context['payments'] = (Payment.objects.for_tenant(self.request.tenant)
                               .filter(reference_type='purchase', reference_id=self.object.pk)
                               .exclude(status='cancelled').order_by('payment_date', 'id'))
        context['can_record_payment'] = permissions.has_perm(
            self.request.user, permissions.PAYMENTS_LEDGER, 'c')
        context['qr'] = _purchase_qr(self.request, self.object)
        return context


class PurchasePDFView(TenantRequiredMixin, PermissionRequiredMixin, View):
    """Branded purchase document as an inline PDF (mirrors the sales invoice)."""

    permission_module = MODULE
    permission_action = 'r'

    def get(self, request, pk):
        purchase = _purchase_for_request(request, pk)
        company = purchase.tenant
        pdf = render_pdf_bytes('purchases/purchase_pdf.html', {
            'purchase': purchase, 'company': company,
            'logo_path': company.logo.path if company.logo else None,
            'qr': _purchase_qr(request, purchase),
        })
        if pdf is None:
            messages.error(request, 'Could not render the purchase PDF.')
            return redirect('purchases:purchase_detail', pk=pk)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="purchase-{purchase.pk}.pdf"'
        return response


class PurchasePaymentView(TenantRequiredMixin, PermissionRequiredMixin, View):
    """Record a payment to the supplier against a purchase (updates paid/status)."""

    permission_module = permissions.PAYMENTS_LEDGER
    permission_action = 'c'
    http_method_names = ['post']

    @transaction.atomic
    def post(self, request, pk):
        purchase = _purchase_for_request(request, pk)
        if purchase.is_cancelled:
            messages.error(request, 'Cannot record a payment on a cancelled purchase.')
            return redirect('purchases:purchase_detail', pk=pk)
        form = RecordPaymentForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Enter a valid payment amount and date.')
            return redirect('purchases:purchase_detail', pk=pk)
        amount = form.cleaned_data['amount']
        pdate = form.cleaned_data['payment_date']
        due = purchase.due_amount or 0
        if amount > due:
            messages.error(request, f'Payment cannot exceed the due amount ({due}).')
            return redirect('purchases:purchase_detail', pk=pk)

        Payment.objects.create(
            tenant=purchase.tenant, depot=purchase.depot, party_type='supplier',
            supplier=purchase.supplier, direction=Payment.Direction.OUT, amount=amount,
            method=form.cleaned_data['method'], payment_date=pdate,
            reference_no=purchase.reference_no or f'PUR-{purchase.pk}',
            reference_type='purchase', reference_id=purchase.pk,
            notes=form.cleaned_data.get('notes', ''),
            created_by=request.user, updated_by=request.user)
        # Reduce the supplier payable.
        LedgerService.post(
            tenant=purchase.tenant, account_type='supplier', account_id=purchase.supplier_id,
            entry_date=pdate, description=f'Payment for purchase #{purchase.pk}',
            debit=amount, credit=0, reference_type='purchase', reference_id=purchase.pk,
            depot=purchase.depot, actor=request.user)
        # Update the bill.
        purchase.paid_amount = (purchase.paid_amount or 0) + amount
        purchase.payment_status = _payment_status(purchase.paid_amount, purchase.total_cost or 0)
        purchase.updated_by = request.user
        purchase.save(update_fields=['paid_amount', 'payment_status', 'updated_by', 'updated_at'])
        log_action(request, 'payment', instance=purchase,
                   after={'amount': str(amount), 'paid': str(purchase.paid_amount), 'due': str(purchase.due_amount)})
        messages.success(request, f'Payment of {amount} recorded — {purchase.get_payment_status_display()}.')
        return redirect('purchases:purchase_detail', pk=pk)


class _PurchaseFormMixin(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin):
    model = Purchase
    permission_module = MODULE
    crud_basename = 'purchase'
    form_class = PurchaseForm
    template_name = 'purchases/purchase_form.html'
    delete_action = 'cancel'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['can_add_party'] = permissions.has_perm(
            self.request.user, permissions.PARTIES, 'c')
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'expense_formset' not in context:
            context['expense_formset'] = PurchaseExpenseFormSet(
                self.request.POST or None, instance=self.object,
                form_kwargs={'tenant': self.request.tenant})
        context['vehicle_capacity_json'] = vehicle_capacity_json(self.request.tenant)
        return context

    @transaction.atomic
    def form_valid(self, form):
        purchase = form.save(commit=False)
        if not purchase.tenant_id:
            purchase.tenant = self.request.tenant
        if not purchase.created_by_id:
            purchase.created_by = self.request.user
        purchase.updated_by = self.request.user
        purchase.save()
        self.object = purchase
        formset = PurchaseExpenseFormSet(
            self.request.POST, instance=purchase,
            form_kwargs={'tenant': self.request.tenant})
        if not formset.is_valid():
            return self.render_to_response(
                self.get_context_data(form=form, expense_formset=formset))
        formset.save()
        purchase.recompute_costs()  # total incl. the dynamic expense lines
        if self.posts_effects:
            _post_purchase_effects(purchase, self.request.user)
            # SaaS per-entry billing — purchases are billable entries too (FR-18).
            SubscriptionService.record_entry_usage(tenant=purchase.tenant, kind='purchase')
        log_action(self.request, 'create' if self.posts_effects else 'update', instance=purchase)
        messages.success(self.request, 'Purchase saved.')
        return redirect(self.crud_url_name('detail'), pk=purchase.pk)


class PurchaseCreateView(_PurchaseFormMixin, CreateView):
    permission_action = 'c'
    posts_effects = True  # post stock/ledger + billing only on first creation


class PurchaseUpdateView(_PurchaseFormMixin, UpdateView):
    permission_action = 'u'
    posts_effects = False  # avoid double-posting stock on edit


class PurchaseCancelView(CrudCancelView):
    model = Purchase
    permission_module = MODULE
    crud_basename = 'purchase'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.is_cancelled:
            _post_purchase_effects(obj, request.user, reverse=True)
        return super().post(request, *args, **kwargs)


class TripListView(CrudListView):
    model = Trip
    permission_module = MODULE
    crud_basename = 'trip'
    delete_action = 'cancel'
    list_display = ['created_at', 'depot', 'material', 'total_qty', 'sold_qty',
                    'excess_qty', 'trip_status', 'status']


class TripDetailView(CrudDetailView):
    model = Trip
    permission_module = MODULE
    crud_basename = 'trip'
    delete_action = 'cancel'
    list_display = ['depot', 'purchase', 'material', 'vehicle', 'source',
                    'total_qty', 'sold_qty', 'excess_qty', 'trip_status', 'status']


class TripCreateView(CrudCreateView):
    model = Trip
    permission_module = MODULE
    crud_basename = 'trip'
    form_class = TripForm


class TripUpdateView(CrudUpdateView):
    model = Trip
    permission_module = MODULE
    crud_basename = 'trip'
    form_class = TripForm


class TripCancelView(CrudCancelView):
    model = Trip
    permission_module = MODULE
    crud_basename = 'trip'
