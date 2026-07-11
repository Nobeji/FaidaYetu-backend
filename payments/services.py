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
        # NOTE: ClickPesa's initiate-ussd-push-request endpoint does NOT accept
        # a per-request callback/webhook URL (only amount, currency,
        # orderReference, phoneNumber, checksum are supported). Passing
        # callback_url here has no effect. To receive PAYMENT RECEIVED /
        # PAYMENT FAILED webhooks you must configure the webhook URL in the
        # ClickPesa Merchant Dashboard -> Settings -> Developers -> Webhooks
        # (or under your Application's webhook settings).
        # See https://docs.clickpesa.com/home/webhooks
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
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if not resp.ok:
            return {'error': resp.text}
        data = resp.json()
        if data.get('status') in ('FAILED',):
            return {'error': data.get('message', 'Transaction failed')}
        return data

    def check_status(self, order_ref):
        # ClickPesa's real query endpoint is GET /third-parties/payments/{orderReference}
        # and it returns a LIST of payment attempts for that order reference,
        # not a single object. See:
        # https://docs.clickpesa.com/api-reference/collection/querying-for-payments/querying-for-payments
        token = self.get_token()
        url = f'{BASE_URL}/payments/{order_ref}'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            return {'error': 'not_found'}
        if not resp.ok:
            return {'error': resp.text}

        data = resp.json()
        results = data if isinstance(data, list) else data.get('data', data.get('results', [data]))
        if not results:
            return {'error': 'not_found'}

        # Multiple attempts can exist for the same orderReference (retries).
        # Prefer the most recently updated one; treat SUCCESS/SETTLED as paid.
        def sort_key(item):
            return item.get('updatedAt') or item.get('createdAt') or ''

        results = sorted(results, key=sort_key, reverse=True)
        success = next((r for r in results if r.get('status') in ('SUCCESS', 'SETTLED')), None)
        latest = success or results[0]
        return latest