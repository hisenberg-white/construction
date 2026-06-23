"""QR codes + signed public-bill tokens (SRS extra: QR on invoice).

A bill's public link carries a signed token (no DB column needed); the public
view validates the signature, so the link is shareable but not guessable.
"""
import base64
import io

import qrcode
from django.core import signing


def qr_data_uri(data, box_size=4, border=2):
    """Return a base64 PNG data URI of a QR code for ``data``."""
    qr = qrcode.QRCode(box_size=box_size, border=border)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def bill_token(pk, salt):
    """Signed, URL-safe token encoding a bill's primary key."""
    return signing.dumps(int(pk), salt=salt)


def bill_pk(token, salt):
    """Decode a signed bill token back to its pk (raises BadSignature)."""
    return signing.loads(token, salt=salt)
