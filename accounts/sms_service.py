import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

AT_BASE_URL = 'https://api.africastalking.com/version1/messaging'


class SmsService:

    def __init__(self):
        self.api_key = getattr(settings, 'AT_API_KEY', '')
        self.username = getattr(settings, 'AT_USERNAME', 'sandbox')
        self.sender_id = getattr(settings, 'AT_SENDER_ID', 'FaidaYetu')

    def send(self, phone, message):
        if not self.api_key:
            logger.warning('AT_API_KEY not configured. SMS not sent.')
            return False

        phone = self._normalize_phone(phone)
        headers = {
            'apikey': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded',
        }
        payload = {
            'username': self.username,
            'to': phone,
            'message': message,
        }
        if self.sender_id:
            payload['from'] = self.sender_id

        try:
            resp = requests.post(AT_BASE_URL, headers=headers, data=payload, timeout=15)
            if resp.status_code == 201:
                data = resp.json()
                recipients = data.get('SMSMessageData', {}).get('Recipients', [])
                if recipients and recipients[0].get('statusCode') == 100:
                    logger.info(f'SMS sent successfully to {phone}')
                    return True
                else:
                    logger.warning(f'SMS delivery failed for {phone}: {data}')
                    return False
            else:
                logger.error(f'SMS API error {resp.status_code}: {resp.text}')
                return False
        except Exception as e:
            logger.error(f'SMS send exception: {e}')
            return False

    def _normalize_phone(self, phone):
        import re
        phone = re.sub(r'[^0-9]', '', phone)
        if phone.startswith('0'):
            phone = '255' + phone[1:]
        elif not phone.startswith('255'):
            phone = '255' + phone
        return '+' + phone
