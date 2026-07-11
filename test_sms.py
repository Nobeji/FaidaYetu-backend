from dotenv import load_dotenv
load_dotenv()
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from accounts.sms_service import SmsService

svc = SmsService()
print('Username:', svc.username)
print('Sender:', svc.sender_id)
result = svc.send('0622837961', "Test SMS from FaidaYetu via Africa's Talking!")
print('Result:', result)