import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class SmsService:

    def __init__(self):
        self.username = getattr(settings, 'AFRICASTALKING_USERNAME', '')
        self.api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '')
        self.sender_id = getattr(settings, 'AFRICASTALKING_SENDER_ID', 'FaidaYetu')

    def send(self, phone, message):
        if not self.username or not self.api_key:
            logger.warning('Africa\'s Talking credentials not configured. SMS not sent.')
            return False

        import re
        phone = re.sub(r'[^0-9]', '', phone)
        if phone.startswith('0'):
            phone = '255' + phone[1:]
        elif not phone.startswith('255'):
            phone = '255' + phone

        to_number = f'+{phone}'

        try:
            import africastalking
            africastalking.initialize(self.username, self.api_key)
            sms = africastalking.SMS
            response = sms.send(message, [to_number], self.sender_id)
            recipients = response.get('SMSMessageData', {}).get('Recipients', [])
            if recipients and recipients[0].get('statusCode') == 101:
                logger.info(f'SMS sent successfully to {to_number}')
                return True
            logger.warning(f'Africa\'s Talking SMS failed: {recipients}')
            return False
        except Exception as e:
            logger.warning(f'Africa\'s Talking SMS error: {e}')
            return False