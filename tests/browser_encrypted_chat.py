"""Chromium acceptance using a loopback model fixture and private mailbox fixture."""
import base64
import json
import os
import pathlib
import secrets
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright
root = pathlib.Path.cwd()
sys.path[:0] = [str(root), str(root / 'stage5')]
from scripts import odin_encrypted_chat as crypto  # noqa: E402
t = tempfile.TemporaryDirectory()
crypto.CONFIG = pathlib.Path(t.name)
k = secrets.token_bytes(32)
p = crypto.CONFIG / 'browser.key'
p.write_bytes(k)
p.chmod(384)

class Model(BaseHTTPRequestHandler):

    def do_POST(self):
        assert self.path == '/v1/chat/completions' and 'Authorization' not in self.headers
        prompt = json.loads(self.rfile.read(int(self.headers['content-length'])))['messages'][-1]['content']
        data = json.dumps({'choices': [{'message': {'content': prompt.upper()}}]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(data)

class Static(SimpleHTTPRequestHandler):

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(root / 'mobile'), **kw)

def start(h):
    s = ThreadingHTTPServer(('127.0.0.1', 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s.server_port
port = start(Model)
site = start(Static)
os.environ.update(ODIN_STAGE5_ENABLE_AI='1', ODIN_LOCAL_MODEL='test', ODIN_LOCAL_PORT=str(port))
with sync_playwright() as w:
    browser = w.chromium.launch(executable_path=os.environ.get('ODIN_TEST_CHROMIUM'), args=['--no-sandbox'])
    page = browser.new_page()
    page.set_default_timeout(6000)
    answers = {}

    def api(r):
        body = r.request.post_data_json if r.request.method == 'POST' else {}
        out = {'authenticated': True} if r.request.url.endswith('/session') else {}
        if r.request.url.endswith('/encrypted-chat'):
            if 'sealed' in body:
                assert 'private test' not in str(body)
                answers[body['id']] = crypto.reply(body)
                out = {'queued': True}
            else:
                out = answers[body['id']]
        r.fulfill(json=out)
    page.route('**/api/**', api)
    page.goto(f'http://127.0.0.1:{site}')
    for tab in ['system', 'activity', 'overview', 'chat']:
        page.locator(f'[data-tab="{tab}"]').click()
        assert page.locator('#view-' + tab).is_visible()
    page.locator('summary', has_text='Pair this browser').click()
    page.fill('#sealedCode', base64.b64encode(k).decode())
    page.click('#sealedPair')
    page.wait_for_function("document.querySelector('#sealedStatus').textContent==='Browser paired'")
    page.reload()
    page.click('[data-tab=chat]')
    page.evaluate("connectPrivateAccess('browser-test-credential-only-1234567890')")
    page.fill('#sealedQuestion', 'private test')
    page.click('#sealedSend')
    page.wait_for_function("document.querySelector('#sealedAnswer').textContent==='PRIVATE TEST'", timeout=8000)
    page.evaluate('lockPrivateAccess()')
    assert page.locator('#sealedAnswer').inner_text() == ''
    print('PASS four navigation tabs, pairing survives reload, WebCrypto → device decrypt → loopback HTTP fixture → device encrypt → browser decrypt, session lock clears answer.')
