"""``{% pagination page_obj %}`` — shared pager for every list screen.

Keeps the current filters (query string) on every page link.
"""
from django import template

register = template.Library()


@register.inclusion_tag('core/_pagination.html', takes_context=True)
def pagination(context, page_obj):
    if page_obj is None or not page_obj.paginator.count:
        return {'show': False}
    paginator = page_obj.paginator
    return {
        'show': True,
        'multi': paginator.num_pages > 1,
        'request': context['request'],
        'page_obj': page_obj,
        'page_range': paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1),
        'ellipsis': paginator.ELLIPSIS,
    }
