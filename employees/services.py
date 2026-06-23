"""PayrollService — computes and posts employee payments (SRS FR-12).

Calculates payable amounts from work logs / monthly salary, applies advances
and deductions, then posts the payment as an expense and to the employee
ledger. Implemented in roadmap Phase 3.
"""
from django.db import transaction


class PayrollService:
    @staticmethod
    def compute_payable(*, employee, period_start, period_end):
        """Compute the amount payable to an employee for a period (SRS FR-12).

        Depends on ``employment_type``: monthly salary, or sum of work-log
        amounts for per-trip/per-load/daily employees.
        """
        raise NotImplementedError('PayrollService.compute_payable — roadmap Phase 3')

    @staticmethod
    @transaction.atomic
    def pay_employee(*, employee, amount, actor=None, advances=0, deductions=0):
        """Record an employee payment as an expense and ledger entry (SRS FR-12)."""
        raise NotImplementedError('PayrollService.pay_employee — roadmap Phase 3')
