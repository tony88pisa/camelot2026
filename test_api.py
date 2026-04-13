import sys, time, hashlib, hmac, requests
from urllib.parse import urlencode

API_KEY = '1c0TtEPfJdTyT2yxdWiYhzvtrvtCLy47F7rm5myFAf511K1PuCp9meGHK1Cq9GfC'
API_SECRET = 'IN4zwGr9oqu2y6Ipib4eYA9FSuDotS06UPzmzBN6j5ychE1Ch1N7C3Zd16KRPNVg'
BASE = 'https://testnet.binance.vision'

# Get server time for accurate timestamp
srv = requests.get(f'{BASE}/api/v3/time').json()
ts = srv['serverTime']
print(f'Server time: {ts}')
print(f'Local time: {int(time.time()*1000)}')
print(f'Delta: {int(time.time()*1000) - ts}ms')

# Build signed request manually
params = {'timestamp': ts, 'recvWindow': 10000}
qs = urlencode(params)
sig = hmac.new(API_SECRET.encode(), qs.encode(), hashlib.sha256).hexdigest()
params['signature'] = sig

headers = {'X-MBX-APIKEY': API_KEY}
resp = requests.get(f'{BASE}/api/v3/account', params=params, headers=headers)
print(f'Status: {resp.status_code}')
if resp.status_code == 200:
    data = resp.json()
    balances = [b for b in data.get('balances', []) if float(b.get('free', 0)) > 0]
    print(f'Account OK! Balances with funds: {len(balances)}')
    for b in balances[:5]:
        asset = b["asset"]
        free = b["free"]
        print(f'  {asset}: {free}')
else:
    print(f'Error: {resp.text}')
