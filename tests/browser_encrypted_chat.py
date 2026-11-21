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
        payload = json.loads(self.rfile.read(int(self.headers['content-length'])))
        prompt = payload["messages"][-1]["content"]
        if prompt == "use project note":
            assert payload["max_tokens"] == 128 and "Sample fact" in payload["messages"][0]["content"]
        answer = prompt.upper()
        if prompt.startswith("Update these UI settings"):
            answer = json.dumps({"heading":"Offline studio","accent":"teal","size":"large"})
        if prompt.startswith("Write one Python expression"):
            assert payload["max_tokens"] == 128
            answer = "len(text.encode())"
        data = json.dumps({'choices': [{'message': {'content': answer}}]}).encode()
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
    page.add_init_script("""
      Object.defineProperty(window, "speechSynthesis", {value: {
        getVoices: () => [{localService:false,lang:"en-US"}, {localService:true,lang:"en-US"}],
        cancel: () => {}, speak: utterance => {window.spoken = utterance;}
      }});
      window.SpeechSynthesisUtterance = class {constructor(text) {this.text = text;}};
    """)
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
    assert not page.locator("#localChatPanel").is_visible()
    page.check("#deviceBridge")
    assert page.locator("#localChatPanel").is_visible()
    page.select_option("#chatModel","cloud")
    assert page.locator("#onlineChatPanel").is_visible() and not page.locator("#localChatPanel").is_visible()
    page.select_option("#chatModel","local")
    page.select_option("#chatMode","work")
    assert page.locator("#deviceWorkPanel").is_visible()
    page.locator('summary', has_text='Pair this browser').click()
    page.fill('#sealedCode', base64.b64encode(k).decode())
    page.click('#sealedPair')
    page.wait_for_function("document.querySelector('#sealedStatus').textContent==='Browser paired'")
    page.reload()
    page.click('[data-tab=chat]')
    page.evaluate("connectPrivateAccess('browser-test-credential-only-1234567890')")
    page.locator("#sealedFile").set_input_files({"name":"note.txt", "mimeType":"text/plain", "buffer":b"private test"})
    page.locator("#sealedStatus").filter(has_text="File loaded locally").wait_for()
    assert page.input_value("#sealedQuestion").endswith("private test")
    assert not answers
    page.fill('#sealedQuestion', 'private test')
    page.click('#sealedSend')
    page.wait_for_function("document.querySelector('#sealedAnswer').textContent.endsWith('PRIVATE TEST')", timeout=8000)
    page.locator("summary", has_text="Voice and webpage excerpts").click()
    assert page.locator("#clipBookmark").get_attribute("href").startswith("javascript:")
    page.click('#readLocal')
    assert page.evaluate('window.spoken.voice.localService && window.spoken.text.endsWith("PRIVATE TEST")')
    page.evaluate('lockPrivateAccess()')
    assert page.locator('#sealedAnswer').inner_text() == ''
    print('PASS four navigation tabs, pairing survives reload, WebCrypto → device decrypt → loopback HTTP fixture → device encrypt → browser decrypt, session lock clears answer.')

    # The installed shell checks the deployed HTML itself, independently of device status.
    import re
    original = (root / "mobile/index.html").read_text()
    updated = re.sub(r'(<meta name="odin-release" content=")[0-9a-f]{16}', r'\g<1>1111222233334444', original)
    page.route("**/?odin_check=*", lambda route: route.fulfill(content_type="text/html", body=updated))
    page.route("**/?odin_release=*", lambda route: route.fulfill(content_type="text/html", body=updated))
    page.fill("#sealedQuestion", "keep draft")
    page.click("#refreshBtn")
    page.locator("#applyAppUpdate").wait_for()
    assert page.input_value("#sealedQuestion") == "keep draft"
    page.fill("#sealedQuestion", "")
    page.click("#applyAppUpdate")
    page.wait_for_url("**/?odin_release=1111222233334444*")
    assert page.locator("meta[name=odin-release]").get_attribute("content") == "1111222233334444"

    import server
    os.environ["ODIN_STAGE5_PROVIDER"] = "local"
    stage = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    server.PORT = stage.server_port
    stage.session_token = secrets.token_urlsafe(32)
    stage.chat_lock = threading.BoundedSemaphore(1)
    threading.Thread(target=stage.serve_forever, daemon=True).start()
    from scripts.odin_note_check import check
    proposal = check("1" * 32, coding=True, port=server.PORT)
    assert proposal["http_status"] == 200 and proposal["match"] and proposal["review"] == "pending"
    page.unroute("**/api/**")
    page.goto(f"http://127.0.0.1:{server.PORT}")
    page.locator("summary", has_text="Device buttons").click()
    page.select_option("#buttonAction", "editor")
    page.click("#buttonBind")
    page.keyboard.press("F8")
    page.locator("#buttonList").filter(has_text="key F8").wait_for()
    page.reload()
    page.keyboard.press("F8")
    assert page.locator("#uiEdits").get_attribute("open") is not None
    page.locator("summary", has_text="Device buttons").click()
    page.evaluate("""() => {
      window.testPad = {id:"Fixture controller", index:0, buttons:[{pressed:false}]};
      Object.defineProperty(navigator, "getGamepads", {value:()=>[window.testPad], configurable:true});
    }""")
    page.select_option("#buttonAction", "chat")
    page.click("#buttonBind")
    page.evaluate("window.testPad.buttons[0].pressed = true")
    page.locator("#buttonList").filter(has_text="Fixture controller button 0").wait_for()
    page.evaluate("window.testPad.buttons[0].pressed = false")
    page.wait_for_timeout(100)
    page.evaluate("window.testPad.buttons[0].pressed = true")
    page.locator('#message:focus').wait_for()
    page.evaluate("window.testPad.buttons[0].pressed = false")
    page.locator("#editStatus").filter(has_text="Ready for an offline edit").wait_for()
    page.fill("#editBrief", "Use a teal heading and larger text")
    page.click("#editSuggest")
    page.locator("#editStatus").filter(has_text="Model suggestion ready").wait_for()
    assert page.input_value("#editAccent") == "teal" and page.input_value("#editSize") == "large"
    page.fill("#editHeading", "Browser preview")
    assert page.locator("[data-odin-chat-heading]").inner_text() == "Browser preview"
    page.click("#editApprove")
    page.locator("#editStatus").filter(has_text="waiting for upload").wait_for()
    page.reload()
    page.locator("[data-odin-chat-heading]").filter(has_text="Browser preview").wait_for()
    page.locator("summary", has_text="Practice notebook").click()
    page.locator("#practiceSummary").filter(has_text="Keep current weights.").wait_for()
    page.locator("summary", has_text="Project note").click()
    page.locator("#noteFile").set_input_files({"name":"facts.md", "mimeType":"text/plain", "buffer":b"Sample fact"})
    page.get_by_text('Loaded. Select Include to use this note.', exact=True).wait_for()
    page.click("#saveNote")
    page.reload()
    page.locator("summary", has_text="Project note").click()
    assert page.input_value("#note") == "Sample fact" and not page.is_checked("#useNote")
    page.check("#useNote")
    page.check("#quick")
    page.fill("#message", "use project note")
    page.click("#send")
    page.locator('#answer').filter(has_text='USE PROJECT NOTE').wait_for()
    page.click("#forgetNote")
    page.reload()
    assert page.input_value("#note") == ""
    page.locator("summary", has_text="Look up Odin code").click()
    page.fill("#symbol", "local_settings")
    page.click("#lookup")
    page.locator("#sourceMatches button").first.click()
    assert page.is_checked("#useNote") and 'ODIN_LOCAL_PORT' in page.input_value("#note")
    assert 'stage5/local_adapter.py:' in page.input_value("#note")
    page.fill("#symbol", "../state")
    page.click("#lookup")
    page.locator("#sourceStatus").filter(has_text="400").wait_for()
    os.environ["ODIN_STAGE5_PROVIDER"] = "groq"
    status = page.evaluate("""async()=> (await fetch('/api/chat',{method:'POST',
      headers:{'Content-Type':'application/json','X-Odin-Request':'chat'},
      body:JSON.stringify({message:'no send',local_options:{reference:'secret',quick:true}})})).status""")
    assert status == 409
    stage.shutdown()
    stage.server_close()
    print("PASS import, save, reload, opt in, local reply limit, forget and cloud refusal.")
