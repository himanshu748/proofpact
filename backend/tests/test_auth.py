import pytest
from fastapi.testclient import TestClient
from backend import main, auth
from backend.store import Store

@pytest.fixture
def accounts(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'store', Store(tmp_path/'accounts.sqlite'))
    def provider(method, **kwargs):
        if method == 'initiate_auth':
            return {'AuthenticationResult': {'AccessToken': kwargs['AuthParameters']['USERNAME'], 'ExpiresIn':3600}}
        if method == 'get_user':
            email=kwargs['AccessToken']; role='builder' if email.startswith('builder') else 'client'
            return {'UserAttributes':[{'Name':k,'Value':v} for k,v in {'sub':email,'name':email.split('@')[0],'email_verified':'false' if email.startswith('unverified') else 'true','custom:role':role}.items()]}
        return {}
    monkeypatch.setattr(auth,'provider',provider)
    with TestClient(main.app) as client, TestClient(main.app) as builder, TestClient(main.app) as outsider:
        for c,email,role in [(client,'client@example.com','client'),(builder,'builder@example.com','builder'),(outsider,'other@example.com','client')]:
            assert c.post('/api/auth/login',json={'email':email,'password':'test-password','role':role}).status_code==200
        yield client,builder,outsider

def test_account_invitation_isolation_and_private_briefs(accounts):
    c,b,o=accounts
    assert c.post('/api/session/role',json={'role':'builder'}).status_code==403
    payload={'name':'Observable delivery','brief':'Build a downloadable report','client':'Client','builder':'Freelancer','requirements':['Download report'],'acceptance_criteria':['CSV contains every filtered row'],'revision_days':5}
    p=c.post('/api/projects',json=payload).json(); path='/api/projects/'+p['id']
    assert o.get(path).status_code==404
    assert b.get(path).status_code==404
    token=c.post(path+'/invite').json()['token']
    assert o.post('/api/invitations/accept',json={'token':token}).status_code==404
    assert b.post('/api/invitations/accept',json={'token':token}).status_code==200
    assert b.get(path).status_code==200
    assert c.post(path+'/invite').status_code==409
    brief={'private_limit_minor':50000,'opening_minor':40000,'deadline':'2026-10-01','notes':'Private client budget'}
    assert c.put(path+'/brief',json=brief).status_code==200
    assert b.get(path+'/brief').json() is None
    assert 'Private client budget' not in b.get(path).text
    assert len(b.get('/api/session').json()['projects'])==1

def test_wrong_role_unverified_and_reset_revocation(accounts):
    c,b,o=accounts
    assert o.post('/api/auth/login',json={'email':'builder@example.com','password':'test-password','role':'client'}).status_code==403
    assert o.post('/api/auth/login',json={'email':'unverified@example.com','password':'test-password','role':'client'}).status_code==403
    assert c.post('/api/auth/reset',json={'email':'client@example.com','code':'123456','password':'Changed-password!1'}).status_code==200
    assert c.get('/api/session').status_code==401

def test_revision_window_requires_agreed_criteria_and_does_not_accept(accounts):
    from backend.domain import create_project,agreement,digest,now
    from datetime import datetime,timedelta,timezone
    c,_,_=accounts
    p=create_project('Report delivery','Build downloadable reports','Client','Freelancer',requirements=['Download CSV'],acceptance_criteria=['CSV includes filtered rows'],revision_days=3)
    p.update(identity_mode='account',members={'client':'client@example.com','builder':'builder@example.com'},owner='client@example.com')
    # Agreement construction uses the same domain function as negotiation.
    a=agreement(p,price=50000,deadline='2026-10-01',version=1)
    p.update(current=a,hash=digest(a),state='SUBMITTED',first_delivery_at=now())
    main.store.put('project#'+p['id'],p);path='/api/projects/'+p['id']+'/revisions'
    assert a['criteria'][0]['title']=='CSV includes filtered rows'
    assert a['revision_policy']['days']==3 and a['delivery_approver']['role']=='client'
    assert c.post(path,json={'criterion_ids':['invented'],'notes':'Please correct this'}).status_code==422
    r=c.post(path,json={'criterion_ids':[a['criteria'][0]['id']],'notes':'CSV omits filtered rows'})
    assert r.status_code==200 and r.json()['state']=='NEEDS_FIX'
    saved=main.store.get('project#'+p['id']);saved['first_delivery_at']=(datetime.now(timezone.utc)-timedelta(days=4)).isoformat();main.store.put('project#'+p['id'],saved)
    assert c.post(path,json={'criterion_ids':[a['criteria'][0]['id']],'notes':'Please correct this'}).status_code==409
    assert main.store.get('project#'+p['id'])['state']=='NEEDS_FIX'

def test_account_agent_grant_revoked_by_password_reset(accounts):
    from backend.tests.test_a2a import send
    c,b,o=accounts
    p=c.post('/api/projects',json={'name':'Agent binding','brief':'Check scoped agent access','client':'Client','builder':'Freelancer','requirements':['Export'],'acceptance_criteria':['Export contains rows']}).json()
    grant=c.post('/api/projects/'+p['id']+'/agent-access',json={'allow_work':False}).json()
    assert send(c,grant['token'],p).json()['result']['task']['status']['state']=='TASK_STATE_COMPLETED'
    assert o.post('/api/projects/'+p['id']+'/agent-access',json={'allow_work':True}).status_code==404
    assert c.post('/api/auth/reset',json={'email':'client@example.com','code':'123456','password':'Changed-password!1'}).status_code==200
    response=send(c,grant['token'],p,mid='after-reset')
    assert response.status_code!=200 or 'error' in response.json()

def test_registration_sends_role_only_at_signup(accounts,monkeypatch):
    calls=[]
    monkeypatch.setattr(auth,'provider',lambda method,**kwargs:calls.append((method,kwargs)) or {})
    c,_,_=accounts
    assert c.post('/api/auth/register',json={'email':'new@example.com','name':'New participant','role':'builder','password':'Example-only!123'}).status_code==200
    assert calls[0][0]=='sign_up'
    assert {'Name':'custom:role','Value':'builder'} in calls[0][1]['UserAttributes']

def test_resubmission_preserves_revision_start(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'store',Store(tmp_path/'delivery.sqlite'))
    from backend.tests.test_integrity import seed,approve_both
    with TestClient(main.app) as c:
        p=approve_both(c,seed(c));path='/api/projects/'+p['id']+'/delivery'
        first=c.post(path,json={'url':'http://127.0.0.1:8000/fixture/fixed'}).json()
        second=c.post(path,json={'url':'http://127.0.0.1:8000/fixture/fixed'}).json()
        assert first['first_delivery_at']==second['first_delivery_at']
