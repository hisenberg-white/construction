"""InvoiceService — creates and voids sale invoices atomically (SRS FR-08, 12.2).

Orchestrates invoice creation: number allocation, line totals, stock-out
postings (via StockService) and customer-ledger postings (via LedgerService).
Implemented in roadmap Phase 2 — signatures are fixed here so views/templates
can be wired against a stable contract.
"""
from django.db import transaction


class InvoiceService:
    @staticmethod
    def next_invoice_no(tenant, depot=None):
        """Allocate the next unique invoice number for the tenant (SRS 12.2).

        Uses the tenant's ``invoice_prefix``; numbers are unique per tenant.
        """
        from .models import SaleInvoice

        prefix = tenant.invoice_prefix or 'INV'
        count = SaleInvoice.objects.for_tenant(tenant).count() + 1
        return f'{prefix}-{count:06d}'

    @staticmethod
    @transaction.atomic
    def create_invoice(*, tenant, depot, customer, lines, actor=None, **header):
        """Create an invoice with its lines, posting stock and ledger impact.

        ``lines`` is an iterable of dicts describing each material/service line.
        TODO (Phase 2): compute totals, decrement stock for material lines via
        StockService, and post the receivable via LedgerService.
        """
        raise NotImplementedError('InvoiceService.create_invoice — roadmap Phase 2')

    @staticmethod
    @transaction.atomic
    def void_invoice(*, invoice, reason, actor=None):
        """Cancel an invoice and reverse its stock/ledger impact (SRS FR-08, FR-17)."""
        raise NotImplementedError('InvoiceService.void_invoice — roadmap Phase 2')
