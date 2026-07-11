import json
import logging
import re
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SMS_API_URL = 'https://api.ehub.co.tz/v1/sms'


class SmsService:

    def __init__(self):
        self.api_key = getattr(settings, 'EHUB_API_KEY', '')
        self.sender_id = getattr(settings, 'EHUB_SENDER_ID', 'PROMOTION')

    def send(self, phone, message):
        if not self.api_key:
            logger.warning('EHUB_API_KEY not configured. SMS not sent.')
            return False

        phone = re.sub(r'[^0-9]', '', phone)
        if phone.startswith('0'):
            phone = '255' + phone[1:]
        elif not phone.startswith('255'):
            phone = '255' + phone

        payload = {
            'from': self.sender_id,
            'to': f'+{phone}',
            'text': message,
        }

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

        try:
            resp = requests.post(
                SMS_API_URL,
                headers=headers,
                json=payload,
                timeout=15,
            )
            if resp.ok:
                logger.info(f'SMS sent successfully to {phone}')
                return True
            logger.warning(f'SMS API returned {resp.status_code}: {resp.text[:200]}')
        except requests.RequestException as e:
            logger.warning(f'SMS API failed: {e}')

        return False
