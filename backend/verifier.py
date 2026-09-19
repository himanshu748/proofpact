"""Fixed, read-only browser tools: no model-generated code or target instructions."""
import csv
import ipaddress
import os
import socket
import time
import logging
import json
import signal
import subprocess
import sys
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse
from .domain import now,uid

DATA=Path(os.getenv('EVIDENCE_PATH','backend/data/evidence'))

def safe_target(url):
    parsed=urlparse(url)
    if parsed.username or parsed.password or parsed.fragment: raise ValueError('Use a URL without credentials or fragments.')
    fixture_origin=os.getenv('FIXTURE_ORIGIN','http://127.0.0.1:8000')
    if os.getenv('DEMO_MODE','true')=='true' and url in [fixture_origin+'/fixture/broken',fixture_origin+'/fixture/fixed']:
        return parsed,None
    if parsed.scheme!='https' or parsed.port not in (None,443): raise ValueError('Delivery must use HTTPS on port 443.')
    allowed=os.getenv('VERIFICATION_ALLOWED_HOSTS','').split(',')
    if parsed.hostname not in allowed: raise ValueError('This target is not enabled for automated browsing. Ask the operator to allowlist its hostname.')
    addresses={x[4][0] for x in socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(x).is_global for x in addresses): raise ValueError('Private, reserved and local addresses cannot be verified.')
    return parsed,sorted(addresses)[0]

def run_verification(p):
    """A crashed browser driver must not leave a pact stuck in VERIFYING."""
    started = time.monotonic()
    child = subprocess.Popen(
        [sys.executable, '-m', 'backend.verifier'], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        output, _ = child.communicate(json.dumps(p), timeout=90)
        if child.returncode: raise RuntimeError('Browser worker exited.')
        return json.loads(output)
    except (subprocess.TimeoutExpired, ValueError, RuntimeError):
        return {'id':uid('run'),'agreement_hash':p['hash'],'version':p['current']['version'],
                'url':p['delivery']['url'],'at':now(),'engine':'Playwright Chromium',
                'duration_ms':round((time.monotonic()-started)*1000),
                'results':[{'criterion_id':c['id'],'title':c['title'],'status':'blocked',
                            'observed':'The browser worker did not complete. No check was certified; retry verification.',
                            'expected':c['description'],'evidence':[]} for c in p['current']['criteria']]}
    finally:
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        child.wait()

def _run_browser(p):
    from playwright.sync_api import sync_playwright
    run={'id':uid('run'),'agreement_hash':p['hash'],'version':p['current']['version'],'url':p['delivery']['url'],'at':now(),'results':[],'engine':'Playwright Chromium','duration_ms':0}
    start=time.monotonic()
    criteria=p['current']['criteria']
    try:
        parsed,ip=safe_target(run['url'])
        with sync_playwright() as pw:
            args=[f'--host-resolver-rules=MAP {parsed.hostname} {ip}'] if ip else []
            if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
                args += ['--single-process', '--no-zygote', '--disable-gpu']
            browser=pw.chromium.launch(headless=True,args=args,timeout=30000)
            try:
                context=browser.new_context(viewport={'width':1280,'height':900},accept_downloads=True,service_workers='block')
                origin=f'{parsed.scheme}://{parsed.netloc}'
                def guard(route):
                    target=urlparse(route.request.url)
                    if f'{target.scheme}://{target.netloc}' != origin or route.request.method not in ('GET','HEAD'): route.abort()
                    else: route.continue_()
                context.route('**/*',guard)
                page=context.new_page();page.set_default_timeout(5000);page.goto(run['url'],timeout=15000,wait_until='domcontentloaded')
                authenticated=False
                for criterion in criteria:
                    result={'criterion_id':criterion['id'],'title':criterion['title'],'status':'blocked','observed':'','expected':criterion['description'],'evidence':[]}
                    try:
                        cid=criterion['id']
                        if cid=='login':
                            page.get_by_label('Email',exact=True).fill('demo@proofpact.local')
                            page.get_by_label('Password',exact=True).fill('DemoPass123!')
                            page.get_by_role('button',name='Sign in',exact=True).click()
                            page.get_by_label('Verification code').wait_for(state='visible')
                            page.get_by_label('Verification code').fill('424242');page.get_by_role('button',name='Verify code').click()
                            page.locator('#dashboard').wait_for(state='visible');authenticated=True
                            result.update(status='passed',observed='Valid credentials and the second factor opened the dashboard.')
                        elif cid=='analytics':
                            if not authenticated: raise ValueError('Login did not complete.')
                            orders=page.get_by_test_id('total-orders').inner_text();revenue=page.get_by_test_id('revenue').inner_text()
                            result.update(status='passed' if orders and revenue else 'failed',observed=f'Total orders: {orders}. Revenue: {revenue}.')
                        elif cid=='otp':
                            text=page.get_by_test_id('verified').inner_text()
                            result.update(status='passed' if text=='Identity verified' else 'failed',observed='Seeded OTP 424242 completed the second factor.')
                        elif cid=='csv':
                            with page.expect_download(timeout=5000) as info: page.get_by_role('button',name='Export CSV').click()
                            download=info.value;path=download.path()
                            if Path(path).stat().st_size>1_000_000: raise ValueError('Downloaded file exceeds the 1 MB limit.')
                            content=Path(path).read_text(); rows=list(csv.DictReader(StringIO(content)))
                            count=len(rows)
                            expected=int(page.get_by_test_id('total-orders').inner_text())
                            result.update(status='passed' if count==expected==27 else 'failed',observed=f'CSV contains {count} of {expected} records. '+('All pages are included.' if count==expected else 'Only the visible page was exported.'))
                            result['evidence'].append({'type':'csv','name':'acme-orders.csv','content':content,'rows':count,'expected_rows':expected})
                        elif cid=='responsive':
                            page.set_viewport_size({'width':390,'height':844})
                            dimensions=page.evaluate('({width:innerWidth, content:document.documentElement.scrollWidth})')
                            result.update(status='review' if dimensions['content']<=dimensions['width'] else 'failed',observed=f"Viewport {dimensions['width']}px; content {dimensions['content']}px. Confirm visual usability from the screenshot.")
                        else:
                            result.update(status='review',observed='This custom requirement needs a human review. No automated result is claimed.')
                        DATA.mkdir(parents=True,exist_ok=True)
                        filename=f"{run['id']}-{cid}.png"
                        page.screenshot(path=str(DATA/filename),full_page=True,timeout=5000)
                        result['evidence'].append({'type':'screenshot','name':filename})
                    except Exception:
                        result.update(status='blocked',observed='The browser could not complete this check. Confirm the target supports the agreed test flow, then rerun.')
                    run['results'].append(result)
            finally: browser.close()
    except Exception as exc:
        logging.getLogger(__name__).warning('Verification browser failed: %s', type(exc).__name__)
        run['results']=[{'criterion_id':c['id'],'title':c['title'],'status':'blocked','observed':'Browser unavailable or target unreachable. Retry when the target and browser are ready.','expected':c['description'],'evidence':[]} for c in criteria]
    run['duration_ms']=round((time.monotonic()-start)*1000)
    return run

if __name__ == '__main__':
    print(json.dumps(_run_browser(json.load(sys.stdin))))
