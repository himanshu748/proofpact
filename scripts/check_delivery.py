"""Exercise the synthetic delivery workflow through its API, including real Chromium."""
import json
import sys
import httpx

base = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:8000'
with httpx.Client(base_url=base, timeout=180) as c:
    def post(path, body=None):
        r = c.post('/api' + path, json=body)
        r.raise_for_status()
        return r.json()
    p = post('/session')['projects'][0]
    path = '/projects/' + p['id']
    agreement_hash = p['hash']
    post(path + '/approve', {'content_hash': agreement_hash, 'reviewed': True})
    post('/session/role', {'role': 'builder'})
    assert post(path + '/approve', {'content_hash': agreement_hash, 'reviewed': True})['state'] == 'AGREEMENT_LOCKED'
    for fixture, expected in [('broken', 'NEEDS_FIX'), ('fixed', 'NEEDS_HUMAN_REVIEW')]:
        post(path + '/delivery', {'url': 'http://127.0.0.1:8000/fixture/' + fixture})
        p = post(path + '/verify')
        assert p['state'] == expected, json.dumps(p['runs'][-1]['results'])
        csv = next(r for r in p['runs'][-1]['results'] if r['criterion_id'] == 'csv')
        assert csv['evidence'][0]['rows'] == (10 if fixture == 'broken' else 27)
        screenshot = next(e['name'] for e in csv['evidence'] if e['type'] == 'screenshot')
        evidence_url = '/api' + path + '/evidence/' + screenshot
        image = c.get(evidence_url)
        assert image.status_code == 200 and image.content.startswith(b'\x89PNG')
        assert httpx.get(base + evidence_url).status_code == 401
    post('/session/role', {'role': 'client'})
    p = post(path + '/human-review', {'criterion_id': 'responsive', 'accepted': True})
    assert p['state'] == 'VERIFIED' and p['hash'] == agreement_hash
    token = post(path + '/share')['token']
    receipt = httpx.get(base + '/api/receipts/' + token).json()
    assert all(not r['evidence'] for r in receipt['run']['results'])
    assert 'private_limit_minor' not in json.dumps(receipt)
    print(json.dumps({'state': p['state'], 'runs': len(p['runs']), 'csv_rows': [10, 27], 'evidence_requires_session': True, 'receipt_redacted': True, 'proof_url': base + '/proof/' + token}))
