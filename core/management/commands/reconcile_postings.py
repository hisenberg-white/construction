"""Bring ledger + stock postings in line with every invoice and purchase.

Fixes documents that were edited before edits posted corrections (the books
kept the original amounts). Safe to run repeatedly — in-sync documents post
nothing.

    python manage.py reconcile_postings --dry-run
    python manage.py reconcile_postings
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.postings import (
    PURCHASE, SALE, actual_postings, expected_invoice_postings,
    expected_purchase_postings, sync_invoice, sync_purchase,
)
from purchases.models import Purchase
from sales.models import SaleInvoice


class Command(BaseCommand):
    help = 'Post corrections so ledger/stock match edited invoices and purchases.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='List out-of-sync documents without posting anything.')

    def handle(self, *args, dry_run=False, **options):
        jobs = [
            ('Invoice', SaleInvoice.objects.select_related('tenant', 'depot'), SALE,
             expected_invoice_postings, sync_invoice, lambda d: d.invoice_no),
            ('Purchase', Purchase.objects.select_related('tenant', 'depot', 'material'), PURCHASE,
             expected_purchase_postings, sync_purchase, lambda d: f'#{d.pk}'),
        ]
        fixed = 0
        for name, qs, spec, expected_fn, sync_fn, label in jobs:
            for doc in qs:
                expected, actual = expected_fn(doc), actual_postings(spec, doc.tenant, doc.pk)
                if _same(expected, actual):
                    continue
                fixed += 1
                self.stdout.write(
                    f'{doc.tenant} — {name} {label(doc)}: '
                    f'account {actual.account} -> {expected.account}; '
                    f'party {_fmt(actual.party)} -> {_fmt(expected.party)}; '
                    f'stock {_fmt(actual.stock)} -> {_fmt(expected.stock)}')
                if not dry_run:
                    with transaction.atomic():
                        sync_fn(doc, actor=None)
        verb = 'Would correct' if dry_run else 'Corrected'
        self.stdout.write(self.style.SUCCESS(f'{verb} {fixed} document(s).'))


def _nonzero(d):
    return {k: v for k, v in d.items() if v}


def _same(a, b):
    return (a.account == b.account and _nonzero(a.party) == _nonzero(b.party)
            and _nonzero(a.stock) == _nonzero(b.stock))


def _fmt(d):
    d = _nonzero(d)
    return ', '.join(f'{k}: {v}' for k, v in d.items()) or '0'
