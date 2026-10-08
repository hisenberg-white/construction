"""Rebuild per-entry usage rows for periods recorded before UsageEntry existed.

Those periods only stored counters (invoice_count / entry_count / sms_count and
amount_due). We list the invoices, purchases and sent SMS created in each such
period (capped at the recorded counts), price each billable row at the period's
average so the rows add up to the amount already billed, and flag them as
``reconstructed``. Any count we can't match to a document becomes an
"Unidentified entry" row so the totals still agree.
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations

CENT = Decimal('0.01')


def backfill(apps, schema_editor):
    Usage = apps.get_model('subscriptions', 'SubscriptionUsage')
    Entry = apps.get_model('subscriptions', 'UsageEntry')
    Invoice = apps.get_model('sales', 'SaleInvoice')
    DeliveryLog = apps.get_model('sales', 'DeliveryLog')
    Purchase = apps.get_model('purchases', 'Purchase')

    for usage in Usage.objects.filter(entries__isnull=True):
        in_period = {'tenant_id': usage.tenant_id,
                     'created_at__date__gte': usage.period_start,
                     'created_at__date__lte': usage.period_end}
        rows = []
        invoices = (Invoice.objects.filter(**in_period).select_related('customer')
                    .order_by('created_at', 'id')[:usage.invoice_count])
        for inv in invoices:
            rows.append(dict(kind='invoice', reference_type='sale_invoice', reference_id=inv.pk,
                             description=f'Invoice {inv.invoice_no} — {inv.customer.name if inv.customer_id else ""}',
                             created_by_id=inv.created_by_id, created_at=inv.created_at, billable=True))
        other = max(usage.entry_count - usage.invoice_count, 0)
        purchases = (Purchase.objects.filter(**in_period).select_related('supplier', 'material')
                     .order_by('created_at', 'id')[:other])
        for p in purchases:
            parts = [p.supplier.name if p.supplier_id else '', p.material.name if p.material_id else '']
            rows.append(dict(kind='purchase', reference_type='purchase', reference_id=p.pk,
                             description=f'Purchase #{p.pk} — {" ".join(x for x in parts if x)}'.strip(),
                             created_by_id=p.created_by_id, created_at=p.created_at, billable=True))
        missing = usage.entry_count - sum(1 for r in rows if r['billable'])
        for _ in range(max(missing, 0)):
            rows.append(dict(kind='entry', reference_type='', reference_id=None,
                             description='Unidentified entry (no matching document found)',
                             created_by_id=None, created_at=None, billable=True))
        sms = (DeliveryLog.objects.filter(**in_period, method='sms', delivery_status='sent')
               .select_related('invoice').order_by('created_at', 'id')[:usage.sms_count])
        for log in sms:
            rows.append(dict(kind='sms', reference_type='sale_invoice', reference_id=log.invoice_id,
                             description=f'SMS for invoice {log.invoice.invoice_no} to {log.recipient}',
                             created_by_id=log.created_by_id, created_at=log.created_at, billable=False))

        billable = sum(1 for r in rows if r['billable'])
        avg = ((usage.amount_due or Decimal('0')) / billable).quantize(CENT, ROUND_HALF_UP) if billable else Decimal('0')
        remainder = (usage.amount_due or Decimal('0')) - avg * billable  # rounding, put on the last row
        last_billable = max((i for i, r in enumerate(rows) if r['billable']), default=None)
        for i, r in enumerate(rows):
            price = avg + (remainder if i == last_billable else 0) if r.pop('billable') else Decimal('0')
            when = r.pop('created_at') or usage.created_at
            Entry.objects.create(usage=usage, tenant_id=usage.tenant_id, price=price,
                                 created_at=when, reconstructed=True, **r)


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0003_usageentry'),
        ('sales', '0002_initial'),
        ('purchases', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
