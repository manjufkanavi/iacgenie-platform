import urllib.request, urllib.parse, json, subprocess

# Get admin token
data = urllib.parse.urlencode({
    'grant_type': 'password',
    'username': 'admin',
    'password': 'ZwbDpB6RJkYRvGSfskSBdP4HjrFqZDdk'
}).encode()

req = urllib.request.Request('http://127.0.0.1:8083/auth/realms/master/protocol/openid-connect/token', data=data)
try:
    resp = urllib.request.urlopen(req)
    token_data = json.loads(resp.read())
    access_token = token_data.get('access_token', '')
    print('Token acquired:', access_token[:20] + '...')
    
    # List existing clients
    req2 = urllib.request.Request('http://127.0.0.1:8083/auth/admin/realms/iacgenie/clients',
                                  headers={'Authorization': 'Bearer ' + access_token})
    resp2 = urllib.request.urlopen(req2)
    clients = json.loads(resp2.read())
    print('\nExisting clients:')
    for c in clients:
        print(f"  {c['clientId']} → redirect: {c.get('redirectUris', 'N/A')}")
except Exception as e:
    print(f'Error: {e}')
