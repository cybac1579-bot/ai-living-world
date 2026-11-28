"""Check travel in the staged subscription UI using synthetic model replies."""
import sys,json,shutil,tempfile
from pathlib import Path
from unittest.mock import patch
from playwright.sync_api import sync_playwright,expect
root=Path(sys.argv[1]).resolve() / 'app/src/main'
sys.path.insert(0,str(root/'python'))
import mobile_embedded as engine
with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
    private=Path(tmp)
    shutil.copytree(root/'assets',private/'resources')
    (private/'auth').mkdir()
    (private/'auth/credentials.json').write_text('{}')
    url=engine.start_engine(private,private/'resources',catalog=lambda **kw:('test',[{'slug':'test-model'}]))
    browser=p.chromium.launch(executable_path=shutil.which('google-chrome'),args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':393,'height':820},has_touch=True)
    page.on('dialog',lambda d:d.accept())
    page.goto(url)
    def menu(): page.locator('#brena-travel-actions summary').click()
    def go(name):
        menu()
        page.get_by_role('button',name='이동 · '+name,exact=True).tap(timeout=10000)
        expect(page.locator('#place')).to_have_text(name)
    go('브레나 촌장 집')
    for reply in ['첫 대답','다음 대답','INVALID']:
        with patch('live_story.request_story',return_value=json.dumps({'npc_id':'BRENA-RANA','speech':reply}) if reply!='INVALID' else 'bad'):
            page.locator('#free-toggle').click()
            page.locator('#free-input').fill('안녕')
            with page.expect_response(lambda r:r.url.endswith('/api/turn')) as response:
                page.locator('#free-form button').click()
            assert response.value.status==(422 if reply=='INVALID' else 200)
            expect(page.locator('#busy')).to_be_hidden()
            if reply!='INVALID': expect(page.locator('#story-content')).to_have_text(reply)
            menu()
            expect(page.get_by_role('button',name='이동 · 브레나 광장',exact=True)).to_be_enabled()
            menu()
    go('브레나 광장')
    page.locator('#free-toggle').click()
    expect(page.locator('#model-tag')).to_contain_text('라나 응답 2회')
    print('PASS two online-bridge turns, invalid reply recovery, travel touch and count in square')
    browser.close()
    engine.stop_engine()
