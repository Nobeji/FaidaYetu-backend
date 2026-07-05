import requests
import json
from django.conf import settings

BASE_URL = 'https://api.clickpesa.com/third-parties'

class ClickPesaService:

    def __init__(self):
        self.client_id = settings.CLICKPESA_CLIENT_ID
        self.api_key = settings.CLICKPESA_API_KEY
        self._token = None

    def generate_token(self):
        url = f'{BASE_URL}/generate-token'
        headers = {
            'client-id': self.client_id,
            'api-key': self.api_key,
            'Content-Type': 'application/json',
        }
        resp = requests.post(url, headers=headers, json={}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            self._token = data.get('token', '').replace('Bearer ', '')
            return self._token
        raise Exception(f'Token generation failed: {resp.text}')

    def get_token(self):
        if not self._token:
            self.generate_token()
        return self._token

    def preview_push(self, phone, amount, order_ref):
        token = self.get_token()
        url = f'{BASE_URL}/payments/preview-ussd-push-request'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'phoneNumber': phone,
            'amount': str(int(amount)),
            'orderReference': order_ref,
            'currency': 'TZS',
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if not resp.ok:
            return {'error': resp.text}
        data = resp.json()
        if not data.get('success', True):
            return {'error': data.get('message', 'Preview failed')}
        return data

    def initiate_push(self, phone, amount, order_ref, callback_url=None):
        token = self.get_token()
        url = f'{BASE_URL}/payments/initiate-ussd-push-request'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'phoneNumber': phone,
            'amount': str(int(amount)),
            'orderReference': order_ref,
            'currency': 'TZS',
        }
        if callback_url:
            payload['callbackUrl'] = callback_url
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if not resp.ok:
            return {'error': resp.text}
        data = resp.json()
        if data.get('status') in ('FAILED',):
            return {'error': data.get('message', 'Transaction failed')}
        return data

    def check_status(self, order_ref):
        token = self.get_token()
        url = f'{BASE_URL}/payments/query'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {'orderReference': order_ref}
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if not resp.ok:
            return {'error': resp.text}
        return resp.json()
