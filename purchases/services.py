"""PurchaseService — records purchases and load splits atomically (SRS FR-07, FR-10).

Posts the purchase, increments depot stock (StockService) and, when bought on
credit, the supplier payable (LedgerService). Implemented in roadmap Phase 2.
"""
from django.db import transaction


class PurchaseService:
    @staticmethod
    @transaction.atomic
    def record_purchase(*, tenant, depot, supplier, material, qty, rate,
                        actor=None, **costs):
        """Record a purchase and add stock; capitalise direct costs (SRS 7.3).

        TODO (Phase 2): compute material_cost/total_cost, post stock-in via
        StockService, and supplier payable via LedgerService when on credit.
        """
        raise NotImplementedError('PurchaseService.record_purchase — roadmap Phase 2')

    @staticmethod
    @transaction.atomic
    def split_trip(*, trip, sold_qty, actor=None):
        """Split an incoming trip into a sale portion and depot excess (SRS FR-10)."""
        raise NotImplementedError('PurchaseService.split_trip — roadmap Phase 2')
