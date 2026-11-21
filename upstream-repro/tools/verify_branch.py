"""Test the unmodified compatibility-branch build in Chromium 109 and current Edge."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from send109 import check as check_send
from zip109 import check as check_import


class Build:
    def __init__(self, directory):
        self.directory = directory

    def read(self, asset):
        path = (self.directory / asset).resolve()
        if not path.is_relative_to(self.directory) or not path.is_file():
            raise KeyError(asset)
        return path.read_bytes()


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('dist', type=Path)
parser.add_argument('chromium109', type=Path)
parser.add_argument('fixture', type=Path)
args = parser.parse_args()
dist = args.dist.resolve(strict=True)
bundle, = (dist / 'static/js').glob('main.*.js')
report = {
    'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=dist.parent, text=True).strip(),
    'mainAsset': bundle.name,
    'mainAssetSha256': hashlib.sha256(bundle.read_bytes()).hexdigest(),
    'fixtureBytes': args.fixture.stat().st_size,
    'fixtureSha256': hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
    'cases': {},
}
with sync_playwright() as pw:
    for name, opts in [('Chromium109', {'executable_path': args.chromium109,
                                        'args': ['--headless', '--disable-background-networking']}),
                       ('Edge', {'channel': 'msedge', 'headless': True})]:
        with pw.chromium.launch(**opts) as browser:
            saved = check_import(browser, Build(dist), args.fixture.resolve(strict=True), False)
            sent = check_send(browser, dist, False)
            report['cases'][name] = {'version': browser.version, 'zipImport': saved, 'shortSend': sent}
            assert saved['runtimeEdits'] == [] and sent['edit'] is None
            assert saved['pageMessage'] == '已导入 1 个对话'
            assert saved['afterReload'] == [{'title': 'Synthetic upgrade check', 'root': '1',
                'links': [['user', '1', None, '2'], ['assistant', '2', '1', None]]}]
            assert sent['messagesRequests'] == ['POST'] and sent['state']['status'] == 'done'
            assert sent['state']['blocks'] == ['FIXTURE_OK'] and 'FIXTURE_OK' in sent['visibleText']
            if name == 'Chromium109':
                assert saved['toSorted'] == sent['nativeToReversed'] == 'undefined'
            print(name, browser.version, 'PASS ZIP import and short send', flush=True)
Path(__file__).with_suffix('.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
