import hashlib, hmac, time, requests, json
from urllib.parse import urlencode

# Base key (senza il primo carattere)
base_key = 'c0TtEPfJdTyT2yxdWiYhzvtrvtCLy47F7rm5myFAf511K1PuCp9meGHK1Cq9GfC'
secret_key = 'IN4zwGr9oqu2y6Ipib4eYA9FSuDotS06UPzmzBN6j5ychE1Ch1N7C3Zd16KRPNVg'
base_url = 'https://testnet.binance.vision'

def sign(params, secret):
    query_string = urlencode(params)
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

variations = ['1', 'l', 'I']

for v in variations:
    api_key = v + base_key
    print(f"Testando variante: {api_key[:5]}...")
    
    server_time = requests.get(f'{base_url}/api/v3/time').json()['serverTime']
    params = {'timestamp': server_time, 'recvWindow': 10000}
    params['signature'] = sign(params, secret_key)
    headers = {'X-MBX-APIKEY': api_key}
    
    resp = requests.get(f'{base_url}/api/v3/account', params=params, headers=headers)
    if resp.status_code == 200:
        print(f" TROVATA! La variante corretta inizia con '{v}'")
        print(f"Chiave completa: {api_key}")
        break
    else:
        print(f" Fallito '{v}': {resp.status_code} {resp.text}")
