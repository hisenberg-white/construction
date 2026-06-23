"""Sale invoice CRUD with line items, delivery log and cancel (SRS FR-08, FR-16)."""
from django.contrib import messages
from django.core import signing
from django.core.mail import EmailMessage
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
    CrudDetailView,
    CrudListView,
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

from .forms import DeliveryLogForm, SaleInvoiceForm, SaleInvoiceLineFormSet
from .models import DeliveryLog, SaleInvoice
from .services import InvoiceService

MODULE = permissions.SALES


def _payment_status(paid, total):
    if paid <= 0:
        return PaymentStatus.UNPAID
    if paid >= total:
        return PaymentStatus.PAID
    return PaymentStatus.PARTIAL


def _invoice_for_request(request, pk):
    qs = SaleInvoice.objects.all()
    if request.tenant is not None:
        qs = qs.for_tenant(request.tenant)
    return get_object_or_404(qs.select_related('customer', 'depot', 'tenant'), pk=pk)


def _invoice_pdf_context(invoice):
    company = invoice.tenant
    return {
        'invoice': invoice,
        'company': company,
        'logo_path': company.logo.path if company.logo else None,
        'lines': invoice.lines.select_related('material', 'service', 'vehicle_type'),
    }


INVOICE_SALT = 'invoice-public'


def _invoice_qr(request, invoice):
    """Data-URI QR of the public (signed) link to this invoice."""
    token = bill_token(invoice.pk, INVOICE_SALT)
    url = request.build_absolute_uri(reverse('sales:invoice_public', args=[token]))
    return qr_data_uri(url)


class InvoicePublicView(View):
    """Read-only branded invoice opened by scanning the QR — no login required
    (access is via the unguessable signed token in the URL)."""

    def get(self, request, token):
        try:
            pk = bill_pk(token, INVOICE_SALT)
        except signing.BadSignature:
            raise Http404
        invoice = get_object_or_404(
            SaleInvoice.objects.select_related('customer', 'depot', 'tenant'), pk=pk)
        company = invoice.tenant
        return render(request, 'sales/invoice_pdf.html', {
            'invoice': invoice, 'company': company,
            'logo_path': company.logo.url if company.logo else None,
            'lines': invoice.lines.select_related('material', 'service', 'vehicle_type'),
        })


def _post_invoice_effects(invoice, actor, *, reverse=False):
    """Post (or reverse) stock-out and the customer receivable for an invoice."""
    for line in invoice.lines.all():
        if line.material_id and line.material.stock_enabled and line.qty:
            txn = (StockLedger.TransactionType.ADJUST_IN if reverse
                   else StockLedger.TransactionType.SALE)
            StockService.record_movement(
                tenant=invoice.tenant, depot=invoice.depot, material=line.material,
                transaction_type=txn, qty=line.qty,
                reference_type='sale_invoice', reference_id=invoice.pk,
                note=('Reversal of ' if reverse else '') + invoice.invoice_no,
                actor=actor,
            )
    due = invoice.due or 0
    if due > 0 and invoice.customer_id:
        # Customer receivable (per-customer credit ledger).
        LedgerService.post(
            tenant=invoice.tenant, account_type='customer',
            account_id=invoice.customer_id, entry_date=invoice.invoice_date,
            description=('Reversal of ' if reverse else '') + f'invoice {invoice.invoice_no}',
            debit=0 if reverse else due, credit=due if reverse else 0,
            reference_type='sale_invoice', reference_id=invoice.pk,
            depot=invoice.depot, actor=actor,
        )
    # Company Sales account — revenue is the full invoice total (SRS FR-14).
    total = invoice.total or 0
    if total > 0:
        LedgerService.post(
            tenant=invoice.tenant, account_type='sales', account_id=None,
            entry_date=invoice.invoice_date,
            description=('Reversal of ' if reverse else '') + f'sale {invoice.invoice_no}',
            debit=total if reverse else 0, credit=0 if reverse else total,
            reference_type='sale_invoice', reference_id=invoice.pk,
            depot=invoice.depot, actor=actor,
        )


class _InvoiceFormMixin(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin):
    model = SaleInvoice
    permission_module = MODULE
    crud_basename = 'invoice'
    form_class = SaleInvoiceForm
    template_name = 'sales/invoice_form.html'
    delete_action = 'cancel'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['tenant'] = self.request.tenant
        kwargs['can_add_party'] = permissions.has_perm(
            self.request.user, permissions.PARTIES, 'c')
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'formset' not in context:
            context['formset'] = SaleInvoiceLineFormSet(
                self.request.POST or None, instance=self.object,
                form_kwargs={'tenant': self.request.tenant},
            )
        context['vehicle_capacity_json'] = vehicle_capacity_json(self.request.tenant)
        return context

    @transaction.atomic
    def form_valid(self, form):
        invoice = form.save(commit=False)
        if not invoice.tenant_id:
            invoice.tenant = self.request.tenant
        if not invoice.created_by_id:
            invoice.created_by = self.request.user
        invoice.updated_by = self.request.user
        invoice.save()
        self.object = invoice
        formset = SaleInvoiceLineFormSet(
            self.request.POST, instance=invoice,
            form_kwargs={'tenant': self.request.tenant},
        )
        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
        formset.save()
        invoice.recompute_totals()
        if self.posts_effects:
            _post_invoice_effects(invoice, self.request.user)
            # SaaS per-entry billing: each invoice is one billable entry (SRS FR-18).
            SubscriptionService.record_entry_usage(tenant=invoice.tenant, kind='invoice')
        log_action(self.request, 'create' if self.posts_effects else 'update', instance=invoice)
        messages.success(self.request, f'Invoice {invoice.invoice_no} saved.')
        return redirect(self.crud_url_name('detail'), pk=invoice.pk)


class InvoiceCreateView(_InvoiceFormMixin, CreateView):
    permission_action = 'c'
    posts_effects = True  # post stock/ledger when the invoice is first created

    def get_initial(self):
        initial = super().get_initial()
        if self.request.tenant:
            initial['invoice_no'] = InvoiceService.next_invoice_no(self.request.tenant)
        return initial


class InvoiceUpdateView(_InvoiceFormMixin, UpdateView):
    permission_action = 'u'
    posts_effects = False  # avoid double-posting stock on edit


class InvoiceListView(CrudListView):
    model = SaleInvoice
    permission_module = MODULE
    crud_basename = 'invoice'
    delete_action = 'cancel'
    list_display = ['invoice_no', 'invoice_date', 'customer', 'total', 'due',
                    'payment_status', 'status']

    def get_queryset(self):
        return super().get_queryset().select_related('customer', 'depot')


class InvoiceDetailView(CrudDetailView):
    model = SaleInvoice
    permission_module = MODULE
    crud_basename = 'invoice'
    delete_action = 'cancel'
    template_name = 'sales/invoice_detail.html'
    list_display = ['invoice_no', 'invoice_date', 'depot', 'customer', 'subtotal',
                    'additional_charges', 'discount', 'tax', 'total', 'paid', 'due',
                    'payment_status', 'status', 'notes']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lines'] = self.object.lines.select_related('material', 'service')
        context['delivery_logs'] = self.object.delivery_logs.all()
        context['delivery_form'] = DeliveryLogForm(tenant=self.request.tenant)
        context['record_payment_form'] = RecordPaymentForm()
        context['payments'] = (Payment.objects.for_tenant(self.request.tenant)
                               .filter(reference_type='sale_invoice', reference_id=self.object.pk)
                               .exclude(status='cancelled').order_by('payment_date', 'id'))
        context['can_record_payment'] = permissions.has_perm(
            self.request.user, permissions.PAYMENTS_LEDGER, 'c')
        context['qr'] = _invoice_qr(self.request, self.object)
        return context


class InvoiceCancelView(CrudCancelView):
    model = SaleInvoice
    permission_module = MODULE
    crud_basename = 'invoice'

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if not obj.is_cancelled:
            _post_invoice_effects(obj, request.user, reverse=True)
        return super().post(request, *args, **kwargs)


class InvoicePaymentView(TenantRequiredMixin, PermissionRequiredMixin, View):
    """Record a customer payment against an invoice (updates paid/due/status)."""

    permission_module = permissions.PAYMENTS_LEDGER
    permission_action = 'c'
    http_method_names = ['post']

    @transaction.atomic
    def post(self, request, pk):
        invoice = _invoice_for_request(request, pk)
        if invoice.is_cancelled:
            messages.error(request, 'Cannot record a payment on a cancelled invoice.')
            return redirect('sales:invoice_detail', pk=pk)
        form = RecordPaymentForm(request.POST)
        if not form.is_valid():
            messages.error(request, 'Enter a valid payment amount and date.')
            return redirect('sales:invoice_detail', pk=pk)
        amount = form.cleaned_data['amount']
        pdate = form.cleaned_data['payment_date']
        due = invoice.due or 0
        if amount > due:
            messages.error(request, f'Payment cannot exceed the due amount ({due}).')
            return redirect('sales:invoice_detail', pk=pk)

        Payment.objects.create(
            tenant=invoice.tenant, depot=invoice.depot, party_type='customer',
            customer=invoice.customer, direction=Payment.Direction.IN, amount=amount,
            method=form.cleaned_data['method'], payment_date=pdate,
            reference_no=invoice.invoice_no, reference_type='sale_invoice',
            reference_id=invoice.pk, notes=form.cleaned_data.get('notes', ''),
            created_by=request.user, updated_by=request.user)
        # Reduce the customer receivable.
        LedgerService.post(
            tenant=invoice.tenant, account_type='customer', account_id=invoice.customer_id,
            entry_date=pdate, description=f'Payment for invoice {invoice.invoice_no}',
            debit=0, credit=amount, reference_type='sale_invoice', reference_id=invoice.pk,
            depot=invoice.depot, actor=request.user)
        # Update the bill.
        invoice.paid = (invoice.paid or 0) + amount
        invoice.due = (invoice.total or 0) - invoice.paid
        invoice.payment_status = _payment_status(invoice.paid, invoice.total or 0)
        invoice.updated_by = request.user
        invoice.save(update_fields=['paid', 'due', 'payment_status', 'updated_by', 'updated_at'])
        log_action(request, 'payment', instance=invoice,
                   after={'amount': str(amount), 'paid': str(invoice.paid), 'due': str(invoice.due)})
        messages.success(request, f'Payment of {amount} recorded — {invoice.get_payment_status_display()}.')
        return redirect('sales:invoice_detail', pk=pk)


class DeliveryLogCreateView(TenantRequiredMixin, PermissionRequiredMixin, CrudContextMixin, CreateView):
    """Record that an invoice was shared by print/email/SMS/WhatsApp (SRS FR-16)."""

    model = SaleInvoice
    permission_module = MODULE
    permission_action = 'u'
    crud_basename = 'invoice'
    form_class = DeliveryLogForm
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        invoice = get_object_or_404(
            SaleInvoice.objects.for_tenant(request.tenant), pk=kwargs['pk'])
        form = DeliveryLogForm(request.POST, tenant=request.tenant)
        if form.is_valid():
            log = form.save(commit=False)
            log.tenant = request.tenant
            log.invoice = invoice
            log.created_by = request.user
            log.updated_by = request.user
            log.save()
            log_action(request, 'email', instance=invoice,
                       after={'method': log.get_method_display(), 'recipient': log.recipient})
            messages.success(request, 'Delivery logged.')
        return redirect('sales:invoice_detail', pk=invoice.pk)


class InvoicePDFView(TenantRequiredMixin, PermissionRequiredMixin, View):
    """Render the branded invoice as a downloadable/inline PDF (SRS FR-08)."""

    permission_module = MODULE
    permission_action = 'r'

    def get(self, request, pk):
        invoice = _invoice_for_request(request, pk)
        context = _invoice_pdf_context(invoice)
        context['qr'] = _invoice_qr(request, invoice)
        pdf = render_pdf_bytes('sales/invoice_pdf.html', context)
        if pdf is None:
            messages.error(request, 'Could not render the invoice PDF.')
            return redirect('sales:invoice_detail', pk=pk)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{invoice.invoice_no}.pdf"'
        return response


class InvoiceEmailView(TenantRequiredMixin, PermissionRequiredMixin, View):
    """Email the invoice PDF to the customer via the tenant's SMTP (SRS FR-16)."""

    permission_module = MODULE
    permission_action = 'u'
    http_method_names = ['post']

    def post(self, request, pk):
        invoice = _invoice_for_request(request, pk)
        config = getattr(invoice.tenant, 'email_config', None)
        if config is None or not config.is_active:
            messages.error(request, 'Set up Email (SMTP) settings before sending.')
            return redirect('sales:invoice_detail', pk=pk)
        recipient = (invoice.customer.email or '').strip()
        if not recipient:
            messages.error(request, 'This customer has no email address on file.')
            return redirect('sales:invoice_detail', pk=pk)

        pdf = render_pdf_bytes('sales/invoice_pdf.html', _invoice_pdf_context(invoice))
        status = DeliveryLog.DeliveryStatus.SENT
        try:
            message = EmailMessage(
                subject=f'Invoice {invoice.invoice_no} from {invoice.tenant.name}',
                body=(f'Dear {invoice.customer.name},\n\n'
                      f'Please find attached invoice {invoice.invoice_no} for '
                      f'{invoice.tenant.default_currency} {invoice.total} '
                      f'(due: {invoice.due}).\n\nThank you,\n{invoice.tenant.name}'),
                from_email=config.sender, to=[recipient],
                connection=config.get_connection(),
            )
            if pdf:
                message.attach(f'{invoice.invoice_no}.pdf', pdf, 'application/pdf')
            message.send()
            messages.success(request, f'Invoice emailed to {recipient}.')
        except Exception as exc:  # surface SMTP errors to the user
            status = DeliveryLog.DeliveryStatus.FAILED
            messages.error(request, f'Email failed: {exc}')

        DeliveryLog.objects.create(
            tenant=invoice.tenant, invoice=invoice,
            method=DeliveryLog.Method.EMAIL, recipient=recipient,
            delivery_status=status, created_by=request.user, updated_by=request.user)
        log_action(request, 'email', instance=invoice,
                   after={'to': recipient, 'status': status})
        return redirect('sales:invoice_detail', pk=pk)
