"""Shared enumerations used across DepotLedger apps."""
from django.db import models


class PaymentMethod(models.TextChoices):
    CASH = 'cash', 'Cash'
    BANK = 'bank', 'Bank Transfer'
    CHEQUE = 'cheque', 'Cheque'
    ONLINE = 'online', 'Online / Wallet'
    CREDIT = 'credit', 'Credit (unpaid)'


class PaymentStatus(models.TextChoices):
    UNPAID = 'unpaid', 'Unpaid'
    PARTIAL = 'partial', 'Partially Paid'
    PAID = 'paid', 'Paid'


class PartyType(models.TextChoices):
    """Which party a payment belongs to (SRS FR-08, FR-12)."""

    CUSTOMER = 'customer', 'Customer'
    SUPPLIER = 'supplier', 'Supplier'
    EMPLOYEE = 'employee', 'Employee'
    VEHICLE = 'vehicle', 'Vehicle / Equipment'
    COMPANY = 'company', 'Company (general)'


class LedgerAccountType(models.TextChoices):
    """Ledger account a transaction posts to (SRS FR-14).

    Per-party accounts carry an ``account_id``; the company-level accounts
    (sales/purchase/expense/cash) are tenant-wide books with no ``account_id``.
    """

    CUSTOMER = 'customer', 'Customer'
    SUPPLIER = 'supplier', 'Supplier'
    EMPLOYEE = 'employee', 'Employee'
    VEHICLE = 'vehicle', 'Vehicle / Equipment'
    SALES = 'sales', 'Sales Account'
    PURCHASE = 'purchase', 'Purchase Account'
    EXPENSE = 'expense', 'Expense Account'
    CASH = 'cash', 'Cash / Bank'


# Company-wide ledger accounts (no per-party account_id).
COMPANY_ACCOUNTS = {
    LedgerAccountType.SALES, LedgerAccountType.PURCHASE,
    LedgerAccountType.EXPENSE, LedgerAccountType.CASH,
}
