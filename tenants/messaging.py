"""Send SMS / WhatsApp through a tenant's own gateway account (SRS FR-16).

Uses only the standard library (urllib) so no extra dependency is needed.
Every sender raises :class:`MessagingError` with a readable reason on failure.
"""
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 15  # seconds

SPARROW_URL = 'https://api.sparrowsms.com/v2/sms/'
AAKASH_URL = 'https://sms.aakashsms.com/sms/v3/send'
TWILIO_URL = 'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json'
META_URL = 'https://graph.facebook.com/v21.0/{phone_id}/messages'


class MessagingError(Exception):
    pass


# --- phone numbers -----------------------------------------------------------

def local_number(phone, country_code):
    """Digits only, without the country code (Sparrow/Aakash want 98XXXXXXXX)."""
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('00'):
        digits = digits[2:]
    if country_code and digits.startswith(country_code) and len(digits) > 10:
        digits = digits[len(country_code):]
    return digits


def international_number(phone, country_code):
    """E.164 form, e.g. +9779812345678 (Twilio / WhatsApp)."""
    raw = (phone or '').strip()
    digits = re.sub(r'\D', '', raw)
    if raw.startswith('+'):
        return f'+{digits}'
    if digits.startswith('00'):
        return f'+{digits[2:]}'
    if country_code and digits.startswith(country_code) and len(digits) > 10:
        return f'+{digits}'
    return f'+{country_code}{digits.lstrip("0")}'


# --- HTTP --------------------------------------------------------------------

def _request(url, *, data=None, json_body=None, headers=None):
    headers = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body).encode()
        headers['Content-Type'] = 'application/json'
    else:
        body = urllib.parse.urlencode(data or {}).encode()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
    req = urllib.request.Request(url, data=body, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            text = resp.read().decode(errors='replace')
    except urllib.error.HTTPError as exc:
        text = exc.read().decode(errors='replace')
        raise MessagingError(f'HTTP {exc.code}: {_error_text(text)}') from exc
    except urllib.error.URLError as exc:
        raise MessagingError(f'Could not reach gateway: {exc.reason}') from exc
    try:
        return json.loads(text)
    except ValueError:
        return {'raw': text}


def _error_text(text):
    try:
        payload = json.loads(text)
    except ValueError:
        return text[:200]
    err = payload.get('error')
    if isinstance(err, dict):
        return err.get('message') or str(err)
    return payload.get('message') or err or text[:200]


def _twilio(sid, token, sender, to, body):
    if not sid:
        raise MessagingError('Twilio account SID is not set.')
    auth = base64.b64encode(f'{sid}:{token}'.encode()).decode()
    _request(TWILIO_URL.format(sid=sid),
             data={'From': sender, 'To': to, 'Body': body},
             headers={'Authorization': f'Basic {auth}'})


# --- public API --------------------------------------------------------------

def send_sms(config, phone, text):
    """Send ``text`` to ``phone`` via the tenant's SMS gateway."""
    if not config.sms_ready:
        raise MessagingError('SMS is not set up for this company.')
    provider = config.sms_provider
    if provider == 'sparrow':
        result = _request(SPARROW_URL, data={
            'token': config.sms_token, 'from': config.sms_sender,
            'to': local_number(phone, config.country_code), 'text': text})
        if result.get('response_code') not in (200, '200'):
            raise MessagingError(result.get('response') or str(result))
    elif provider == 'aakash':
        result = _request(AAKASH_URL, data={
            'auth_token': config.sms_token,
            'to': local_number(phone, config.country_code), 'text': text})
        if result.get('error'):
            raise MessagingError(result.get('message') or str(result))
    elif provider == 'twilio':
        _twilio(config.sms_account_sid, config.sms_token, config.sms_sender,
                international_number(phone, config.country_code), text)
    else:
        raise MessagingError(f'Unknown SMS provider: {provider}')


def send_whatsapp(config, phone, text, template_params=None):
    """Send a WhatsApp message. With Meta and a template name set, sends that
    approved template filled with ``template_params`` instead of ``text``."""
    if not config.whatsapp_ready:
        raise MessagingError('WhatsApp is not set up for this company.')
    to = international_number(phone, config.country_code)
    provider = config.whatsapp_provider
    if provider == 'meta':
        body = {'messaging_product': 'whatsapp', 'to': to.lstrip('+')}
        if config.whatsapp_template:
            body.update(type='template', template={
                'name': config.whatsapp_template,
                'language': {'code': config.whatsapp_template_language or 'en'},
                'components': [{
                    'type': 'body',
                    'parameters': [{'type': 'text', 'text': str(p)}
                                   for p in (template_params or [])],
                }],
            })
        else:
            body.update(type='text', text={'body': text})
        _request(META_URL.format(phone_id=config.whatsapp_sender), json_body=body,
                 headers={'Authorization': f'Bearer {config.whatsapp_token}'})
    elif provider == 'twilio':
        sender = config.whatsapp_sender
        if not sender.startswith('whatsapp:'):
            sender = f'whatsapp:{international_number(sender, config.country_code)}'
        _twilio(config.whatsapp_account_sid, config.whatsapp_token, sender,
                f'whatsapp:{to}', text)
    else:
        raise MessagingError(f'Unknown WhatsApp provider: {provider}')
