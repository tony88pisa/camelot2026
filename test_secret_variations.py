import hashlib, hmac, time, requests, json
from urllib.parse import urlencode

# Base keys
api_key = '1c0TtEPfJdTyT2yxdWiYhzvtrvtCLy47F7rm5myFAf511K1PuCp9meGHK1Cq9GfC'
base_secret = 'N4zwGr9oqu2y6Ipib4eYA9FSuDotS06UPzmzBN6j5ychE1Ch1N7C3Zd16KRPNVg'
base_url = 'https://testnet.binance.vision'

def sign(params, secret):
    query_string = urlencode(params)
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

variations = ['I', '1', 'l']

print("Attempting Secret Key variations...")
for v in variations:
    secret_key = v + base_secret
    print(f"Testing Secret starting with '{v}'...")
    
    server_time = requests.get(f'{base_url}/api/v3/time').json()['serverTime']
    params = {'timestamp': server_time, 'recvWindow': 10000}
    params['signature'] = sign(params, secret_key)
    headers = {'X-MBX-APIKEY': api_key}
    
    resp = requests.get(f'{base_url}/api/v3/account', params=params, headers=headers)
    if resp.status_code == 200:
        print(f"WINNER! Correct Secret starts with '{v}'")
        print(f"Updated Secret: {secret_key}")
        # Salviamo nel .env se troviamo quella giusta
        break
    else:
        print(f"Failed '{v}': {resp.status_code}")
