"""Compare the v0.1.3 release with one in-memory compatibility edit on Chromium 109."""
import argparse
import hashlib
import json
import mimetypes
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright


def check(browser, site, replace_reverse):
    context = browser.new_context(locale="zh-CN", service_workers="block")
    origin = "http://127.0.0.1:18766"
    messages = []
    reply = [
        {"type": "message_start", "message": {}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "FIXTURE_OK"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn", "title": "Probe"}},
        {"type": "message_stop"},
    ]

    def route_local(route):
        url = urlsplit(route.request.url)
        if url.hostname == "api.deepseek.com" and url.path == "/anthropic/v1/messages":
            messages.append(route.request.method)
            return route.fulfill(content_type="text/event-stream", headers={"access-control-allow-origin":"*"},
                                 body="".join("data: " + json.dumps(event) + "\n\n" for event in reply))
        if url.hostname != "127.0.0.1":
            return route.abort()
        path = (site / (unquote(url.path).lstrip("/") or "index.html")).resolve()
        if not path.is_relative_to(site) or not path.is_file():
            return route.fulfill(status=404, body="")
        data = path.read_bytes()
        if replace_reverse and path.name == "main.4fc5bb07.js":
            assert data.count(b".toReversed()") == 1
            data = data.replace(b".toReversed()", b".slice().reverse()")
        return route.fulfill(body=data, content_type="application/javascript" if path.suffix == ".js"
                             else mimetypes.guess_type(path.name)[0] or "application/octet-stream")

    context.route("**/*", route_local)
    context.add_init_script("""localStorage.setItem('chat-demo:locale','zh-CN');
        localStorage.setItem('chat-demo:api-key','synthetic');""")
    page = context.new_page()
    page.goto(origin)
    field = page.locator("textarea").first
    field.fill("Synthetic test.")
    page.locator('button[aria-label="发送"][aria-disabled="false"]').wait_for()
    field.press('Enter')
    read_state = """async () => {
        const db = await new Promise(ok => {const r = indexedDB.open('chat-demo');r.onsuccess = () => ok(r.result)})
        try {
            const session = await new Promise(ok => {const r = db.transaction('sessions').objectStore('sessions').getAll();r.onsuccess = () => ok(r.result[0])})
            const answer = session?.messages.find(m => m.role === 'assistant')
            return answer && {status:answer.status, error:answer.error, blocks: answer.blocks.map(b => b.text)}
        } finally {db.close()}
    }"""
    state = None
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        state = page.evaluate(read_state)
        if state and state.get("status") in ("done", "error"):
            break
        page.wait_for_timeout(100)
    row = {"edit": ".slice().reverse()" if replace_reverse else None, "messagesRequests": messages,
           "nativeToReversed": page.evaluate("typeof Array.prototype.toReversed"), "state": state,
           "visibleText": page.locator("body").inner_text()}
    context.close()
    return row


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("site", type=Path)
    parser.add_argument("chromium", type=Path)
    args = parser.parse_args()
    site = args.site.resolve()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=args.chromium, args=["--headless","--disable-background-networking"])
        result = {"browser": browser.version, "releaseMainSha256": hashlib.sha256((site / "static/js/main.4fc5bb07.js").read_bytes()).hexdigest(),
                  "cases": [check(browser, site, patch) for patch in (False, True)]}
        browser.close()
    Path(__file__).with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in result["cases"]:
        print(row["edit"], row["messagesRequests"], row["state"])
