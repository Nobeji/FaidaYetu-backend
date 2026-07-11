import hashlib
import hmac
import json
import requests
from django.conf import settings


def send_sms(phone, message):
    api_key = settings.EHUB_API_KEY
    api_secret = settings.EHUB_API_SECRET
    sender_id = settings.EHUB_SENDER_ID

    payload = {
        'from': sender_id,
        'to': phone,
        'text': message,
    }
    body = json.dumps(payload, separators=(',', ':'))

    signature = hmac.new(
        api_secret.encode('utf-8'),
        body.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    headers = {
        'Authorization': f'Bearer {api_key}',
        'X-Signature': signature,
        'Content-Type': 'application/json',
    }

    try:
        resp = requests.post(
            'https://api.ehub.co.tz/v1/sms/send',
            headers=headers,
            data=body,
            timeout=15,
        )
        return resp.ok
    except requests.RequestException:
        return False
