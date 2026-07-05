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
        url = f'{BASE_URL}/collection/ussd-push/preview'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'mobileNumber': phone,
            'amount': str(int(amount)),
            'orderReference': order_ref,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        return resp.json() if resp.ok else {'error': resp.text}

    def initiate_push(self, phone, amount, order_ref, callback_url=None):
        token = self.get_token()
        url = f'{BASE_URL}/collection/ussd-push/initiate'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'mobileNumber': phone,
            'amount': str(int(amount)),
            'orderReference': order_ref,
            'externalId': order_ref,
        }
        if callback_url:
            payload['callbackUrl'] = callback_url
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        return resp.json() if resp.ok else {'error': resp.text}

    def check_status(self, order_ref):
        token = self.get_token()
        url = f'{BASE_URL}/collection/query'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {'orderReference': order_ref}
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        return resp.json() if resp.ok else {'error': resp.text}
