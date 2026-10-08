"""Pagination helper for screens that aren't ListViews (ledger books, stock)."""
from django.core.paginator import Paginator

PER_PAGE = 50


def paginate(request, items, per_page=PER_PAGE):
    """Return the requested page of ``items`` (invalid page numbers fall back
    to the first/last page) as ``(page_obj, is_paginated)``."""
    page_obj = Paginator(items, per_page).get_page(request.GET.get('page'))
    return page_obj, page_obj.paginator.num_pages > 1
