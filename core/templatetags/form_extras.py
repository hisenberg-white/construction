"""Template helpers for rendering bound form fields nicely."""
from django import template

from core.dates import ad_to_bs_str

register = template.Library()


@register.filter
def npdate(value, with_time=True):
    """Render an AD date/datetime as a Nepali (BS) date string."""
    return ad_to_bs_str(value, with_time=with_time)

# Widgets that should span the full form width.
_WIDE = {'Textarea'}
# Widgets rendered as a toggle/checkbox row.
_BOOL = {'CheckboxInput'}


@register.filter
def widget_type(field):
    """Return the widget class name of a bound field (e.g. 'TextInput')."""
    return field.field.widget.__class__.__name__


@register.filter
def field_col(field):
    """Bootstrap column class chosen by widget type."""
    wt = field.field.widget.__class__.__name__
    if wt in _WIDE or wt in _BOOL:
        return 'col-12'
    return 'col-md-6'


@register.filter
def is_checkbox(field):
    return field.field.widget.__class__.__name__ in _BOOL
