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
    print(f"Testing variation starting with '{v}'...")
    
    try:
        server_time = requests.get(f'{base_url}/api/v3/time').json()['serverTime']
        params = {'timestamp': server_time, 'recvWindow': 10000}
        params['signature'] = sign(params, secret_key)
        headers = {'X-MBX-APIKEY': api_key}
        
        resp = requests.get(f'{base_url}/api/v3/account', params=params, headers=headers)
        if resp.status_code == 200:
            print(f"SUCCESS: Variation '{v}' is CORRECT!")
            print(f"Final Key: {api_key}")
            break
        else:
            print(f"FAILED '{v}': HTTP {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"ERROR on variation '{v}': {str(e)}")
