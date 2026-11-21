"""Compare the upstream release and an in-memory one-line fix with a synthetic backup."""
import argparse
import hashlib
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlsplit
from zipfile import ZipFile

from playwright.sync_api import sync_playwright


def check(browser, release, fixture, patch):
    origin = 'http://127.0.0.1:38941'
    patched_assets = []
    with browser.new_context(locale='zh-CN', viewport={'width': 1280, 'height': 860}) as ctx:
        def asset(route):
            u = urlsplit(route.request.url)
            if u.netloc != urlsplit(origin).netloc:
                return route.abort()
            path = u.path.lstrip('/') or 'index.html'
            try:
                data = release.read(path)
            except KeyError:
                return route.fulfill(status=404)
            old = b'.messages.toSorted('
            if patch and path.endswith('.js') and old in data:
                assert data.count(old) == 1
                data = data.replace(old, b'.messages.slice().sort(')
                patched_assets.append(path)
            return route.fulfill(body=data, content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
        ctx.route('**/*', asset)
        ctx.add_init_script("localStorage.setItem('chat-demo:api-key','fixture'); localStorage.setItem('chat-demo:locale','zh-CN')")
        page = ctx.new_page()
        page.goto(origin)
        page.get_by_role('button', name='设置', exact=True).click()
        page.get_by_role('tab').last.click()
        with page.expect_file_chooser() as chooser:
            page.get_by_role('button', name='上传', exact=True).click()
        chooser.value.set_files(fixture)
        page.get_by_role('button', name='确认导入', exact=True).click()
        message = page.get_by_text('已导入 1 个对话', exact=True).or_(page.get_by_text('文件导入失败，', exact=False)).first
        message.wait_for(timeout=10000)
        status = message.inner_text()
        page.reload()
        page.locator('textarea').wait_for()
        sessions = page.evaluate("""async () => {
          const db = await new Promise((ok,fail) => {
            const q=indexedDB.open('chat-demo');q.onsuccess=()=>ok(q.result);q.onerror=()=>fail(q.error)
          });
          try { const rows = await new Promise((ok,fail) => {
            const q=db.transaction('sessions').objectStore('sessions').getAll(); q.onsuccess=()=>ok(q.result); q.onerror=()=>fail(q.error)
          }); return rows.map(s=>({title:s.title,root:s.rootMessageId,links:s.messages.map(m=>[m.role,m.id,m.parentId,m.selectedChildId])})) }
          finally { db.close() }
        }""")
        return dict(engine=browser.version, toSorted=page.evaluate('typeof Array.prototype.toSorted'),
                    pageMessage=status, afterReload=sessions, runtimeEdits=patched_assets)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('release', type=Path)
    cli.add_argument('chromium109', type=Path)
    cli.add_argument('fixture', type=Path)
    args = cli.parse_args()
    out = {'releaseSHA256': hashlib.sha256(args.release.read_bytes()).hexdigest(),
           'fixtureBytes': args.fixture.stat().st_size, 'cases': {}}
    with ZipFile(args.release) as release, sync_playwright() as pw:
        with pw.chromium.launch(executable_path=args.chromium109, args=['--headless','--disable-background-networking']) as old:
            for name, patch in [('original109', False), ('oneChange109', True)]:
                out['cases'][name] = check(old, release, args.fixture, patch)
        with pw.chromium.launch(channel='msedge', headless=True) as current:
            out['cases']['originalEdge'] = check(current, release, args.fixture, False)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    Path(__file__).with_suffix('.json').write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    original, fixed, control = out['cases'].values()
    assert original['toSorted'] == 'undefined' and '文件导入失败' in original['pageMessage'] and original['afterReload'] == []
    assert len(fixed['runtimeEdits']) == 1 and fixed['afterReload'] == control['afterReload'] and '已导入 1 个对话' in fixed['pageMessage']
    assert fixed['afterReload'][0]['links'] == [['user','1',None,'2'], ['assistant','2','1',None]]
