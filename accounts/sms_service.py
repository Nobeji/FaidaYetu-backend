import hashlib
import hmac
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SmsService:

    def __init__(self):
        self.api_key = getattr(settings, 'EHUB_API_KEY', '')
        self.api_secret = getattr(settings, 'EHUB_API_SECRET', '')
        self.sender_id = getattr(settings, 'EHUB_SENDER_ID', 'PROMOTION')

    def send(self, phone, message):
        if not self.api_key or not self.api_secret:
            logger.warning('EHUB_API_KEY or EHUB_API_SECRET not configured. SMS not sent.')
            return False

        import re
        phone = re.sub(r'[^0-9]', '', phone)
        if phone.startswith('0'):
            phone = '255' + phone[1:]
        elif not phone.startswith('255'):
            phone = '255' + phone

        payload = {
            'from': self.sender_id,
            'to': phone,
            'text': message,
        }
        body = json.dumps(payload, separators=(',', ':'))

        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            body.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            'Authorization': f'Bearer {self.api_key}',
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
            if resp.ok:
                logger.info(f'SMS sent successfully to {phone}')
                return True
            else:
                logger.error(f'SMS API error {resp.status_code}: {resp.text}')
                return False
        except requests.RequestException as e:
            logger.error(f'SMS send exception: {e}')
            return False
