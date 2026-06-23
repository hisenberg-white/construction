"""AD <-> BS (Bikram Sambat) date helpers (SRS NFR: Localization / Nepali date)."""
import datetime

import nepali_datetime


def ad_to_bs_str(value, with_time=True):
    """Format an AD date/datetime as a BS (Nepali) ``YYYY-MM-DD`` string."""
    if value is None or value == '':
        return ''
    if isinstance(value, datetime.datetime):
        bs = nepali_datetime.date.from_datetime_date(value.date())
        text = f'{bs.year}-{bs.month:02d}-{bs.day:02d}'
        return f'{text} {value:%H:%M}' if with_time else text
    if isinstance(value, datetime.date):
        bs = nepali_datetime.date.from_datetime_date(value)
        return f'{bs.year}-{bs.month:02d}-{bs.day:02d}'
    return str(value)


def bs_to_ad(year, month, day):
    """Convert a BS year/month/day to an AD :class:`datetime.date`."""
    return nepali_datetime.date(int(year), int(month), int(day)).to_datetime_date()


def uses_bs(request):
    tenant = getattr(request, 'tenant', None)
    return bool(tenant and getattr(tenant, 'default_calendar', 'AD') == 'BS')
