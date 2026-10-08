"""Upload paths that file reference images per company.

Layout::

    references/<company>/<kind>/<YYYY>/<MM>/<company>_<kind>_<doc no>_<timestamp>.<ext>

e.g. ``references/sane-construction-pvt-ltd/invoices/2026/10/
sane-construction-pvt-ltd_invoices_inv-000002_20261008-143005.jpg``.
The original file extension is kept; only the name is replaced.
"""
import os

from django.utils import timezone
from django.utils.deconstruct import deconstructible
from django.utils.text import slugify


def company_slug(tenant):
    if tenant is None:
        return 'no-company'
    return slugify(tenant.name) or f'company-{tenant.pk}'


@deconstructible
class ReferenceImagePath:
    """``upload_to`` callable; ``number_field`` names the document-number
    field included in the file name (when it is filled in)."""

    def __init__(self, kind, number_field=None):
        self.kind = kind
        self.number_field = number_field

    def __call__(self, instance, filename):
        ext = os.path.splitext(filename)[1].lower() or '.jpg'
        company = company_slug(getattr(instance, 'tenant', None))
        now = timezone.localtime()
        parts = [company, self.kind]
        number = slugify(getattr(instance, self.number_field, '') or '') if self.number_field else ''
        if number:
            parts.append(number)
        parts.append(now.strftime('%Y%m%d-%H%M%S'))
        return '/'.join([
            'references', company, self.kind, now.strftime('%Y'), now.strftime('%m'),
            '_'.join(parts) + ext,
        ])

    def __eq__(self, other):
        return (isinstance(other, ReferenceImagePath)
                and (self.kind, self.number_field) == (other.kind, other.number_field))
