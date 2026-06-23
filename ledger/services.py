"""LedgerService — posts double-sided ledger entries (SRS FR-14, 7.1, 12.2).

Every financial transaction posts through here so each party account keeps a
correct running ``balance_after``. Debit increases a receivable (customer owes
more); credit decreases it. Never hand-edit balances.
"""
from decimal import Decimal

from django.db import transaction

from .models import LedgerEntry


class LedgerService:
    @staticmethod
    def account_balance(tenant, account_type, account_id):
        last = (
            LedgerEntry.objects.for_tenant(tenant)
            .filter(account_type=account_type, account_id=account_id)
            .order_by('-entry_date', '-id')
            .first()
        )
        return last.balance_after if last else Decimal('0')

    @staticmethod
    @transaction.atomic
    def post(*, tenant, account_type, account_id, entry_date, description='',
             debit=0, credit=0, reference_type='', reference_id=None,
             depot=None, actor=None):
        """Append a ledger entry and update the running balance."""
        debit, credit = Decimal(debit), Decimal(credit)
        balance = LedgerService.account_balance(tenant, account_type, account_id)
        balance = balance + debit - credit
        return LedgerEntry.objects.create(
            tenant=tenant,
            depot=depot,
            account_type=account_type,
            account_id=account_id,
            entry_date=entry_date,
            description=description,
            debit=debit,
            credit=credit,
            balance_after=balance,
            reference_type=reference_type,
            reference_id=reference_id,
            created_by=actor,
            updated_by=actor,
        )
