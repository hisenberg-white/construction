"""HTML-to-PDF rendering via xhtml2pdf (used for invoice PDFs, SRS FR-08/FR-16)."""
import os
from io import BytesIO

from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa


def _link_callback(uri, rel):
    """Resolve <img>/CSS URIs to absolute filesystem paths for xhtml2pdf."""
    if os.path.isabs(uri) and os.path.exists(uri):
        return uri
    media_url, static_url = settings.MEDIA_URL, settings.STATIC_URL
    for url, root in ((media_url, settings.MEDIA_ROOT),
                      (static_url, getattr(settings, 'STATIC_ROOT', None) or '')):
        url = url or ''
        for candidate in (url, '/' + url.lstrip('/')):
            if url and uri.startswith(candidate):
                path = os.path.join(root, uri[len(candidate):].lstrip('/\\'))
                if os.path.exists(path):
                    return path
    return uri


def render_pdf_bytes(template_name, context):
    """Render a template to PDF bytes, or ``None`` on failure."""
    html = render_to_string(template_name, context)
    buffer = BytesIO()
    status = pisa.CreatePDF(html, dest=buffer, link_callback=_link_callback)
    if status.err:
        return None
    return buffer.getvalue()
