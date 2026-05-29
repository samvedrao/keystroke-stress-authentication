import urllib.request
import urllib.parse
import http.cookiejar
import json
import time

base = 'http://127.0.0.1:5000'
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

username = f'testuser_{int(time.time())}'
email = username + '@example.com'
password = 'password123'

# Register user (form POST)
reg_data = urllib.parse.urlencode({'username': username, 'email': email, 'password': password}).encode('utf-8')
req = urllib.request.Request(base + '/register', data=reg_data, method='POST')
resp = opener.open(req)
print('register status', resp.getcode())

# Visit setup page to get session cookie
resp = opener.open(base + '/setup-typing')
print('setup get', resp.getcode())

# Prepare baseline payload
sample = 'hello world this is a sample'
keystrokes = []
start = int(time.time() * 1000)
for i, ch in enumerate(sample):
    keystrokes.append({'timestamp': start + i*120, 'key': ch})

payload = {'typed_text': sample, 'keystroke_data': keystrokes}
json_data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(base + '/save-baseline', data=json_data, method='POST')
req.add_header('Content-Type', 'application/json')
resp = opener.open(req)
print('save-baseline status', resp.getcode())
print('response:', resp.read().decode('utf-8'))
