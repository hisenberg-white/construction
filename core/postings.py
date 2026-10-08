"""Keep a document's ledger + stock postings in line with the document.

Sale invoices and purchases post to three books when created:

* the party account (customer receivable / supplier payable) — the amount due,
* the company account (Sales / Purchase) — the document total,
* the stock ledger — the quantities moved.

Both books are append-only, so when a document is **edited** we never rewrite
old rows. Instead :func:`sync_postings` compares what the document says *now*
with what has actually been posted for it (summed by reference) and appends
correction rows for the difference. Party payments post under the same
reference, so "expected party balance" is simply the document's current due.

The same function repairs documents that drifted before this existed (see the
``reconcile_postings`` management command).
"""
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Sum

ZERO = Decimal('0')


@dataclass
class Postings:
    """Net amounts per book, all in the document's natural direction."""
    party: dict = field(default_factory=dict)    # account_id -> net amount
    account: Decimal = ZERO                       # company account net
    stock: dict = field(default_factory=dict)     # (depot_id, material_id) -> net qty


@dataclass(frozen=True)
class Spec:
    """How a document type posts (direction of each book)."""
    ref_type: str
    party_type: str          # 'customer' | 'supplier'
    party_debit: bool        # customer receivable is a debit, supplier payable a credit
    account_type: str        # 'sales' | 'purchase'
    account_debit: bool      # purchase account is a debit, sales a credit
    stock_out: bool          # sales take stock out, purchases bring it in


SALE = Spec('sale_invoice', 'customer', True, 'sales', False, True)
PURCHASE = Spec('purchase', 'supplier', False, 'purchase', True, False)


def actual_postings(spec, tenant, ref_id):
    """What the ledger and stock books currently hold for this document."""
    from inventory.models import StockLedger
    from ledger.models import LedgerEntry

    entries = LedgerEntry.objects.filter(tenant=tenant, reference_type=spec.ref_type,
                                         reference_id=ref_id)
    result = Postings()
    for row in (entries.filter(account_type=spec.party_type)
                .values('account_id').annotate(d=Sum('debit'), c=Sum('credit'))):
        net = (row['d'] or ZERO) - (row['c'] or ZERO)
        result.party[row['account_id']] = net if spec.party_debit else -net
    acc = entries.filter(account_type=spec.account_type).aggregate(d=Sum('debit'), c=Sum('credit'))
    net = (acc['d'] or ZERO) - (acc['c'] or ZERO)
    result.account = net if spec.account_debit else -net

    for row in (StockLedger.objects.filter(tenant=tenant, reference_type=spec.ref_type,
                                           reference_id=ref_id)
                .values('depot_id', 'material_id').annotate(i=Sum('qty_in'), o=Sum('qty_out'))):
        net = (row['o'] or ZERO) - (row['i'] or ZERO)
        result.stock[(row['depot_id'], row['material_id'])] = net if spec.stock_out else -net
    return result


def sync_postings(spec, doc, expected, *, actor, label, entry_date, depot):
    """Append correction rows so the books match ``expected``. Returns the
    number of rows posted (0 when already in sync)."""
    from inventory.models import MaterialItem, StockLedger
    from inventory.services import StockService
    from ledger.services import LedgerService
    from tenants.models import DepotLocation

    tenant = doc.tenant
    actual = actual_postings(spec, tenant, doc.pk)
    posted = 0
    note = f'Correction to {label}'

    def post_ledger(account_type, account_id, amount, debit_side):
        # ``amount`` > 0 adds on the book's natural side; < 0 takes it back.
        nonlocal posted
        if not amount:
            return
        on_debit = debit_side if amount > 0 else not debit_side
        LedgerService.post(
            tenant=tenant, account_type=account_type, account_id=account_id,
            entry_date=entry_date, description=note,
            debit=abs(amount) if on_debit else 0, credit=0 if on_debit else abs(amount),
            reference_type=spec.ref_type, reference_id=doc.pk, depot=depot, actor=actor)
        posted += 1

    for account_id in set(actual.party) | set(expected.party):
        diff = expected.party.get(account_id, ZERO) - actual.party.get(account_id, ZERO)
        post_ledger(spec.party_type, account_id, diff, spec.party_debit)
    post_ledger(spec.account_type, None, expected.account - actual.account, spec.account_debit)

    keys = set(actual.stock) | set(expected.stock)
    depots = DepotLocation.objects.in_bulk({k[0] for k in keys})
    materials = MaterialItem.objects.in_bulk({k[1] for k in keys})
    for key in keys:
        diff = expected.stock.get(key, ZERO) - actual.stock.get(key, ZERO)
        if not diff:
            continue
        more = diff > 0  # more stock moved in the document's direction
        if spec.stock_out:
            txn = StockLedger.TransactionType.SALE if more else StockLedger.TransactionType.ADJUST_IN
        else:
            txn = StockLedger.TransactionType.PURCHASE if more else StockLedger.TransactionType.ADJUST_OUT
        StockService.record_movement(
            tenant=tenant, depot=depots[key[0]], material=materials[key[1]],
            transaction_type=txn, qty=abs(diff),
            reference_type=spec.ref_type, reference_id=doc.pk, note=note, actor=actor)
        posted += 1
    return posted


# --- per document type -------------------------------------------------------

def expected_invoice_postings(invoice):
    if invoice.is_cancelled:
        return Postings()
    stock = defaultdict(lambda: ZERO)
    for line in invoice.lines.select_related('material'):
        if line.material_id and line.material.stock_enabled and line.qty:
            stock[(invoice.depot_id, line.material_id)] += line.qty
    party = {invoice.customer_id: invoice.due or ZERO} if invoice.customer_id else {}
    return Postings(party=party, account=invoice.total or ZERO, stock=dict(stock))


def expected_purchase_postings(purchase):
    if purchase.is_cancelled:
        return Postings()
    stock = {}
    if purchase.material_id and purchase.material.stock_enabled and purchase.qty:
        stock[(purchase.depot_id, purchase.material_id)] = purchase.qty
    party = ({purchase.supplier_id: purchase.due_amount or ZERO}
             if purchase.supplier_id else {})
    return Postings(party=party, account=purchase.total_cost or ZERO, stock=stock)


def sync_invoice(invoice, actor):
    return sync_postings(SALE, invoice, expected_invoice_postings(invoice), actor=actor,
                         label=f'invoice {invoice.invoice_no}',
                         entry_date=invoice.invoice_date, depot=invoice.depot)


def sync_purchase(purchase, actor):
    return sync_postings(PURCHASE, purchase, expected_purchase_postings(purchase), actor=actor,
                         label=f'purchase #{purchase.pk}',
                         entry_date=purchase.purchase_date, depot=purchase.depot)
