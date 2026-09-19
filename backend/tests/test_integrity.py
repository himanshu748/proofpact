import copy
import json
import pytest
from fastapi.testclient import TestClient
from backend import main
from backend.domain import digest
from backend.store import Store,Conflict

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'store',Store(tmp_path/'test.sqlite'))
    with TestClient(main.app) as c:
        yield c

def seed(c):
    r=c.post('/api/session');assert r.status_code==200
    return r.json()['projects'][0]

def approve_both(c,p):
    assert c.post(f"/api/projects/{p['id']}/approve",json={'content_hash':p['hash'],'reviewed':True}).status_code==200
    c.post('/api/session/role',json={'role':'builder'})
    r=c.post(f"/api/projects/{p['id']}/approve",json={'content_hash':p['hash'],'reviewed':True})
    assert r.json()['state']=='AGREEMENT_LOCKED'
    return r.json()

def test_private_data_is_structurally_separate(client):
    p=seed(client)
    public=json.dumps(p)
    assert 'private_limit_minor' not in public and '650000' not in public
    brief=client.get(f"/api/projects/{p['id']}/brief").json()
    assert brief['private_limit_minor']==800000
    client.post('/api/session/role',json={'role':'builder'})
    brief=client.get(f"/api/projects/{p['id']}/brief").json()
    assert brief['private_limit_minor']==650000
    assert client.get(f"/api/projects/{p['id']}/briefs/client").status_code==404

def test_separate_demo_workspaces_cannot_read_each_other(client):
    p=seed(client)
    with TestClient(main.app) as other:
        seed(other)
        assert other.get(f"/api/projects/{p['id']}").status_code==404
        assert other.get(f"/api/projects/{p['id']}/brief").status_code==404

def test_approval_requires_current_hash_and_explicit_review(client):
    p=seed(client);path=f"/api/projects/{p['id']}/approve"
    assert client.post(path,json={'content_hash':'stale','reviewed':True}).status_code==409
    assert client.post(path,json={'content_hash':p['hash'],'reviewed':False}).status_code==422
    r=client.post(path,json={'content_hash':p['hash'],'reviewed':True})
    assert r.json()['state']=='AWAITING_APPROVAL'
    assert set(r.json()['approvals'])=={'client'}

def test_cannot_submit_before_lock_or_as_client(client):
    p=seed(client);path=f"/api/projects/{p['id']}/delivery"
    assert client.post(path,json={'url':'http://127.0.0.1:8000/fixture/fixed'}).status_code==403
    client.post('/api/session/role',json={'role':'builder'})
    assert client.post(path,json={'url':'http://127.0.0.1:8000/fixture/fixed'}).status_code==409

def test_scope_change_preserves_locked_hash(client):
    p=approve_both(client,seed(client));client.post('/api/session/role',json={'role':'client'})
    r=client.post(f"/api/projects/{p['id']}/changes",json={'text':'Also add payments and dark mode.'}).json()
    assert r['changes'][-1]['classification']=='scope_change'
    assert r['hash']==p['hash'] and r['current']==p['current']

def test_amendment_requires_new_dual_approval(client):
    p=approve_both(client,seed(client))
    path=f"/api/projects/{p['id']}"
    r=client.post(path+'/amend',json={'included':['Login','Payments'],'price_minor':900000,'deadline':'2026-09-25'}).json()
    assert r['hash']==p['hash'] and r['current']==p['current'] and r['approvals']==p['approvals']
    assert r['state']=='AGREEMENT_LOCKED'
    pending=r['pending_amendment']
    assert pending['agreement']['version']==4 and pending['approvals']=={}
    assert client.post(path+'/amendment/approve',json={'content_hash':p['hash'],'reviewed':True}).status_code==409
    assert client.post(path+'/amendment/approve',json={'content_hash':pending['hash'],'reviewed':False}).status_code==422
    payload={'content_hash':pending['hash'],'reviewed':True}
    r=client.post(path+'/amendment/approve',json=payload).json()
    assert r['hash']==p['hash'] and r['state']=='AGREEMENT_LOCKED'
    client.post('/api/session/role',json={'role':'client'})
    r=client.post(path+'/amendment/approve',json=payload).json()
    assert r['hash']==pending['hash'] and r['state']=='AGREEMENT_LOCKED'
    assert r['current']['version']==4 and r['pending_amendment'] is None
    assert r['agreements'][0]['hash']==p['hash'] and len(r['approvals'])==2

def test_pending_change_does_not_invalidate_delivery_or_existing_verification(client):
    p=approve_both(client,seed(client));path=f"/api/projects/{p['id']}"
    before=client.post(path+'/delivery',json={'url':'http://127.0.0.1:8000/fixture/fixed'}).json()
    r=client.post(path+'/amend',json={'included':['Login','Payments'],'price_minor':900000,'deadline':'2026-09-25'}).json()
    assert r['state']=='SUBMITTED' and r['delivery']==before['delivery'] and r['hash']==p['hash']
    payload={'content_hash':r['pending_amendment']['hash'],'reviewed':True}
    r=client.post(path+'/amendment/reject',json=payload).json()
    assert r['delivery']==before['delivery'] and r['hash']==p['hash'] and r['pending_amendment'] is None


def test_cannot_share_unverified_pact(client):
    p=approve_both(client,seed(client))
    assert client.post(f"/api/projects/{p['id']}/share").status_code==409

def test_cannot_edit_frozen_brief(client):
    p=seed(client)
    assert client.put(f"/api/projects/{p['id']}/brief",json={'private_limit_minor':10000,'opening_minor':9000,'deadline':'2026-09-22','notes':''}).status_code==409

def test_csrf_origin_rejected(client):
    assert client.post('/api/session',headers={'Origin':'https://evil.example'}).status_code==403

def test_deployed_origin_does_not_trust_localhost(client, monkeypatch):
    monkeypatch.setenv('PUBLIC_ORIGIN', 'https://proof.example')
    assert client.post('/api/session', headers={'Origin': 'http://localhost:3000'}).status_code == 403
    assert client.post('/api/session', headers={'Origin': 'https://proof.example'}).status_code == 200

def test_verifier_exception_restores_retryable_state(client, monkeypatch):
    p = approve_both(client, seed(client))
    path = f"/api/projects/{p['id']}"
    assert client.post(path + '/delivery', json={'url': 'http://127.0.0.1:8000/fixture/fixed'}).status_code == 200
    def failed(_): raise RuntimeError('browser launch failed')
    monkeypatch.setattr(main, 'run_verification', failed)
    assert client.post(path + '/verify').status_code == 503
    p = client.get(path).json()
    assert p['state'] == 'SUBMITTED' and p['runs'] == []

def test_public_receipt_redacts_evidence_without_mutating_private_run(client):
    p = seed(client)
    stored = main.store.get('project#' + p['id'])
    stored['state'] = 'VERIFIED'
    stored['runs'] = [{'results': [{'evidence': [{'type': 'csv', 'content': 'private cells'}, {'type': 'screenshot', 'name': 'private.png'}]}]}]
    main.store.put('project#' + p['id'], stored)
    token = client.post(f"/api/projects/{p['id']}/share").json()['token']
    with TestClient(main.app) as anonymous:
        receipt = anonymous.get('/api/receipts/' + token).json()
        assert receipt['run']['results'][0]['evidence'] == []
        assert 'private cells' not in json.dumps(receipt)
    assert len(client.get(f"/api/projects/{p['id']}").json()['runs'][0]['results'][0]['evidence']) == 2

def test_url_gate_rejects_private_and_unapproved_targets(monkeypatch):
    from backend.verifier import safe_target
    for url in ['http://example.com','https://127.0.0.1','https://169.254.169.254','https://user:pass@example.com','file:///etc/passwd','http://127.0.0.1:8000/fixture/fixed?redirect=bad']:
        with pytest.raises(ValueError): safe_target(url)
    monkeypatch.setenv('VERIFICATION_ALLOWED_HOSTS','example.com')
    monkeypatch.setattr('backend.verifier.socket.getaddrinfo',lambda *a,**k:[(2,1,6,'',('10.0.0.1',443))])
    with pytest.raises(ValueError): safe_target('https://example.com')

def test_optimistic_write_rejects_concurrent_update(tmp_path):
    store=Store(tmp_path/'race.sqlite');a=store.put('key',{'value':1});b=copy.deepcopy(a)
    store.put('key',{**a,'value':2})
    with pytest.raises(Conflict):store.put('key',{**b,'value':3})

def test_hash_is_order_independent_but_content_sensitive():
    assert digest({'b':1,'a':2})==digest({'a':2,'b':1})
    assert digest({'price_minor':750000})!=digest({'price_minor':750001})
