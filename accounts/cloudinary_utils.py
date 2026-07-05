import hashlib
import time
import requests
from django.conf import settings

def upload_image(file_obj, folder='faidayetu/products'):
    cloud_name = settings.CLOUDINARY_CLOUD_NAME
    api_key = settings.CLOUDINARY_API_KEY
    api_secret = settings.CLOUDINARY_API_SECRET
    base_url = f'https://api.cloudinary.com/v1_1/{cloud_name}'

    timestamp = int(time.time())
    params = {'folder': folder, 'timestamp': timestamp}
    signature = _sign(params, api_secret)
    params['api_key'] = api_key
    params['signature'] = signature

    files = {'file': file_obj}
    resp = requests.post(f'{base_url}/image/upload', data=params, files=files, timeout=30)
    if resp.status_code == 200:
        return resp.json().get('secure_url', '')
    raise Exception(f'Cloudinary upload failed: {resp.text}')

def _sign(params, api_secret):
    sorted_keys = sorted(params.keys())
    sign_str = '&'.join(f'{k}={params[k]}' for k in sorted_keys) + api_secret
    return hashlib.sha256(sign_str.encode('utf-8')).hexdigest()
