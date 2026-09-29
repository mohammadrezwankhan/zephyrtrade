"""Exercise the shipped HTML in Chromium without real network navigation.

This harness uses set_content because this environment's administrator blocks
file:// and localhost navigation. Scenario persistence uses an explicit in-memory
Storage test double. It verifies UI logic, not native durable browser storage or
end-to-end browser-to-server integration. Real local HTTP is tested in pytest.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright, expect

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--chromium',default='/usr/bin/chromium')
parser.add_argument('--output',type=Path,default=root/'docs/champion/evidence')
args=parser.parse_args()
args.output.mkdir(parents=True,exist_ok=True)
shots=args.output/'screenshots';shots.mkdir(exist_ok=True)
html=(root/'ZephyrTrade-Champion.html').read_text()
checks=[]
errors=[]

def record(name,details=''):
    checks.append({'check':name,'status':'PASS','details':details})

def instrument(store=None):
    # A transparent storage double and an observation hook for actual Blob payloads.
    encoded=json.dumps(store or {}).replace('</', '<\\/')
    fixture=f'''<script>
    (()=>{{
    window.__store={encoded};window.__denyStorage=false;window.__exports=[];
    Object.defineProperty(window,'localStorage',{{configurable:true,value:{{
      getItem:k=>Object.prototype.hasOwnProperty.call(window.__store,k)?window.__store[k]:null,
      setItem:(k,v)=>{{if(window.__denyStorage)throw new DOMException('Test quota','QuotaExceededError');window.__store[k]=String(v);}},
      removeItem:k=>{{delete window.__store[k];}},clear:()=>{{window.__store={{}};}}
    }}}});
    const originalCreateURL=URL.createObjectURL.bind(URL);
    URL.createObjectURL=blob=>{{window.__exports.push(blob);return originalCreateURL(blob);}};
    }})();
    </script>'''
    return html.replace('</head>',fixture+'</head>')

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000},device_scale_factor=1)
    page=context.new_page();page.set_default_timeout(5000)
    page.on('pageerror',lambda e:errors.append(str(e)))
    downloads=[];page.on('download',lambda d:downloads.append(d.suggested_filename))
    def capture(name):
        # Capture settled real app state at the top, not a scrolled full-page composite.
        page.locator('#page-title').click()
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(120)
        expect(page.locator('#toast')).to_be_hidden(timeout=7000)
        page.screenshot(path=str(shots/name),full_page=True)

    begin=time.perf_counter();page.set_content(instrument(),wait_until='load')
    expect(page.locator('#page-title')).to_have_text('From wind to value.')
    elapsed=time.perf_counter()-begin
    metrics=page.evaluate('ZephyrApp.getVisibleMetrics()')
    assert metrics['rows']==3888
    assert abs(metrics['total']-18761431.424600992)<1e-6
    assert page.locator('#model-select option').count()==9
    record('Initial snapshot and nine strategies',f"3888 hours, full-precision revenue agrees; one set_content load {elapsed:.3f}s (not network performance).")
    capture('overview-desktop.png')
    page.get_by_role('button',name='Prices',exact=True).click()
    assert page.locator('svg[role="img"]').count()>0
    page.get_by_role('button',name='Revenue',exact=True).click()
    expect(page.locator('#page-content')).to_contain_text('Perfect foresight')
    page.get_by_role('button',name='Output',exact=True).click()
    record('Three chart modes and benchmark disclosure')
    page.get_by_role('button',name='7 days',exact=True).click()
    ids=page.evaluate('ZephyrApp.getVisibleMetrics().rows')
    assert 0<ids<=168
    page.locator('#model-select').select_option('persistence_24h')
    assert page.evaluate('ZephyrApp.getState().model')=='persistence_24h'
    record('Period and strategy changes recompute metrics',str(ids)+' retained hours in 7-day window')
    page.get_by_role('button',name='Custom',exact=True).click()
    page.locator('#from-date').fill('2024-12-31');page.locator('#to-date').fill('2024-12-01')
    page.get_by_role('button',name='Apply',exact=True).click()
    expect(page.locator('#filter-error')).to_be_visible()
    page.locator('#from-date').fill('2024-07-21');page.locator('#to-date').fill('2024-07-21')
    page.get_by_role('button',name='Apply',exact=True).click()
    assert 0<page.evaluate('ZephyrApp.getVisibleMetrics().rows')<=24
    record('Invalid date ordering rejected; one-day window recovers')
    # Synthetic out-of-range custom dates exercise the empty state, not fabricated rows.
    page.locator('#from-date').fill('2025-01-01');page.locator('#to-date').fill('2025-01-02')
    page.get_by_role('button',name='Apply',exact=True).click()
    expect(page.locator('#page-content')).to_contain_text('No records in this period.')
    page.get_by_role('button',name='All data',exact=True).click()
    record('Empty date range has explicit recovery')
    page.get_by_role('link',name='Model arena').click()
    expect(page.locator('#page-title')).to_have_text('Let the evidence lead.')
    assert page.locator('tbody tr').count()==9
    capture('model-arena-desktop.png')
    page.locator('#export-models').click()
    text=page.evaluate('window.__exports.at(-1).text()')
    assert len(text.strip().splitlines())==10 and 'capture_pct' in text
    record('Nine-row model ranking and comparison CSV payload')
    page.get_by_role('link',name='Data explorer').click()
    expect(page.locator('#page-title')).to_have_text('Every number, traceable.')
    assert page.locator('tbody tr').count()==25
    first=page.locator('tbody tr').first.inner_text()
    page.get_by_role('button',name='Next',exact=True).click()
    assert page.locator('tbody tr').first.inner_text()!=first
    page.locator('#data-search').fill('2024-12-15')
    assert 0<page.locator('tbody tr').count()<=24
    page.locator('#export-filtered').click()
    text=page.evaluate('window.__exports.at(-1).text()')
    assert 'synthetic_research' in text and '2024-12-15' in text
    assert len(text.strip().splitlines())<=25
    page.locator('#data-search').fill('not-a-date')
    expect(page.locator('tbody')).to_contain_text('No matching records.')
    page.locator('#data-search').fill('')
    record('Ledger pagination, search, empty state and filtered CSV payload')
    page.get_by_role('link',name='Strategy lab').click()
    expect(page.locator('#optimal-offer')).to_contain_text('9.00')
    page.locator('#da').fill('999')
    expect(page.locator('#lab-stale')).to_be_visible()
    expect(page.locator('#save-scenario')).to_be_disabled()
    page.get_by_role('link',name='Overview').click()
    page.get_by_role('link',name='Strategy lab').click()
    expect(page.locator('#da')).to_have_value('999')
    expect(page.locator('#save-scenario')).to_be_disabled()
    page.get_by_role('button',name='Calculate optimal offer').click()
    expect(page.locator('#lab-error')).to_be_visible()
    page.locator('#da').fill('400');page.locator('#up').fill('600');page.locator('#down').fill('200')
    page.locator('#scenarios').fill('2,8,20');page.locator('#probabilities').fill('.2,.5,.3')
    page.get_by_role('button',name='Calculate optimal offer').click()
    expect(page.locator('#optimal-offer')).to_contain_text('8.00')
    expect(page.locator('#expected-revenue')).to_contain_text('3,200.00')
    expect(page.locator('#lab-stale')).to_be_hidden()
    record('Dirty assumptions, draft navigation retention, invalid prices and recovery')
    capture('strategy-lab-desktop.png')
    page.locator('#hours').fill('0.25');page.get_by_role('button',name='Calculate optimal offer').click()
    expect(page.locator('#expected-revenue')).to_contain_text('800.00')
    record('Quarter-hour settlement scaling in UI')
    page.locator('#save-scenario').click()
    expect(page.locator('#save-dialog')).to_be_visible()
    page.locator('#scenario-name').fill('<script>not executable</script>')
    page.locator('#save-form button[type=submit]').click()
    expect(page.locator('#saved-list')).to_contain_text('<script>not executable</script>')
    assert page.locator('#saved-list script').count()==0
    store=page.evaluate('window.__store')
    assert 'zephyr-scenarios-v1' in store
    record('Scenario save and escaped names through Storage test double','Native durable storage NOT verified in this harness.')
    page.locator('#export-scenario').click()
    scenario=json.loads(page.evaluate('window.__exports.at(-1).text()'))
    assert scenario['calculated']['expected_revenue_dkk']==800
    page.locator('#export-curve').click()
    assert 'user_assumptions' in page.evaluate('window.__exports.at(-1).text()')
    record('Scenario JSON and revenue-curve CSV payloads')
    page.locator('#scenario-file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{invalid'})
    expect(page.locator('#toast')).to_contain_text('Import failed:')
    scenario['input']['hours']=1
    page.locator('#scenario-file').set_input_files({'name':'scenario.json','mimeType':'application/json','buffer':json.dumps(scenario).encode()})
    expect(page.locator('#hours')).to_have_value('1')
    expect(page.locator('#expected-revenue')).to_contain_text('3,200.00')
    record('Invalid import rejected; valid JSON imports and recalculates')
    page.evaluate('window.__denyStorage=true')
    page.locator('#save-scenario').click();page.locator('#scenario-name').fill('Quota test')
    page.locator('#save-form button[type=submit]').click()
    expect(page.locator('#toast')).to_contain_text('Could not save')
    expect(page.locator('#save-dialog')).to_be_visible()
    page.get_by_role('button',name='Cancel',exact=True).click()
    page.evaluate('window.__denyStorage=false')
    record('Storage failure is not reported as a successful save','Fault injection into explicit Storage double.')
    page.on('dialog',lambda dialog:dialog.accept())
    page.locator('[data-delete-saved]').click()
    expect(page.locator('#saved-list')).to_contain_text('Your experiments belong here.')
    record('Delete confirmation and in-memory storage update')
    # Hydrate an actual saved app record via an explicit storage fixture on a fresh DOM.
    page.close()
    page=context.new_page();page.set_default_timeout(5000)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('download',lambda d:downloads.append(d.suggested_filename))
    page.set_content(instrument(store),wait_until='load')
    page.get_by_role('link',name='Strategy lab').click()
    expect(page.locator('#saved-list')).to_contain_text('not executable')
    page.locator('[data-load-saved]').click()
    expect(page.locator('#hours')).to_have_value('0.25')
    record('Saved-record hydration and loading','Fixture rehydration, not an OS/browser persistence claim.')
    page.locator('#verify-python').click()
    expect(page.locator('#page-title')).to_have_text('Know what you are seeing.')
    record('Unavailable optional solver leads to setup, not fabricated success')
    page.locator('#export-provenance').click()
    provenance=json.loads(page.evaluate('window.__exports.at(-1).text()'))
    assert provenance['quality']['rows']==3888 and len(provenance['sources'])==2
    record('Provenance JSON exposes source hashes and exclusions')
    page.get_by_role('button',name='Open quick guide').click()
    expect(page.locator('#guide-dialog')).to_be_visible()
    assert page.evaluate("document.querySelector('#guide-dialog').contains(document.activeElement)")
    page.keyboard.press('Escape');expect(page.locator('#guide-dialog')).to_be_hidden()
    expect(page.locator('#help-button')).to_be_focused()
    record('Dialog focus entry, Escape and focus return')
    page.get_by_role('link',name='Overview').click();page.locator('#model-select').select_option('direct_regression')
    for width,height in [(1440,1000),(1024,900),(768,1024),(390,844),(320,740)]:
        page.set_viewport_size({'width':width,'height':height})
        for name in ['Overview','Strategy lab','Model arena','Data explorer','Method & evidence']:
            page.get_by_role('link',name=name,exact=False).click()
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),(width,name,'overflow')
        if width==390:
            page.get_by_role('link',name='Overview').click()
            capture('overview-mobile.png')
            page.get_by_role('link',name='Strategy lab').click()
            capture('strategy-lab-mobile.png')
    record('Responsive overflow check across five pages and five viewports','1440, 1024, 768, 390, 320 CSS px; emulation only.')
    page.locator('#theme-top').click()
    assert page.locator('html').get_attribute('data-theme')=='light'
    page.set_viewport_size({'width':1440,'height':1000})
    page.get_by_role('link',name='Overview').click()
    capture('overview-light.png')
    record('Light theme and mobile-accessible theme toggle')
    page.emulate_media(reduced_motion='reduce')
    assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
    transition=page.locator('.button').first.evaluate('el=>getComputedStyle(el).transitionDuration')
    assert transition in ['0s','1e-05s','0.00001s','0.01ms'],transition
    record('Reduced-motion preference respected',transition)
    # DOM checks are not a comprehensive accessibility audit.
    missing=page.evaluate("""() => [...document.querySelectorAll('button,input:not([type=file]),select,textarea')].filter(el=>el.getClientRects().length && !el.disabled && !(el.innerText?.trim()||el.getAttribute('aria-label')||el.labels?.length||el.getAttribute('title'))).map(el=>el.outerHTML)""")
    assert not missing,missing
    record('Visible controls have DOM labels or accessible-name sources','No screen-reader or full WCAG conformance claim.')
    assert not errors,errors
    record('No uncaught JavaScript exceptions across exercised journeys')
    result={'status':'PASS','harness':'Chromium set_content; in-memory Storage double; no file or localhost browser navigation',
            'browser':browser.version,'checks':checks,'javascript_errors':errors,
            'browser_download_events':downloads,
            'limitations':['Native persistent storage and real file opening blocked by administrator policy',
                           'Actual browser-to-Python navigation blocked; Python HTTP API tested separately',
                           'Screenshots are actual rendered app, not a concept mockup',
                           'Human UAT, real devices and assistive-technology testing not performed']}
    (args.output/'browser-checks.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    browser.close()
