import copy
import hashlib
import hmac
import pytest
from fastapi.testclient import TestClient
from backend import main, payments
from backend.store import Store

@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'store', Store(tmp_path/'payments.sqlite'))
    monkeypatch.setenv('PAYMENTS_MODE','razorpay_test')
    monkeypatch.setenv('RAZORPAY_KEY_ID','rzp_test_fixture')
    monkeypatch.setenv('RAZORPAY_KEY_SECRET','test-fixture-secret')
    monkeypatch.setenv('RAZORPAY_LINKED_ACCOUNT_ID','acc_fixture')
    calls=[]
    order={}
    def request(self,method,path,data=None):
        calls.append((method,path,data))
        if method=='POST':
            order.update(copy.deepcopy(data),id='order_fixture',status='created',amount_paid=0,amount_due=data['amount'])
            order['transfers']={'items':[]}
        if method=='PATCH':
            order['transfers']['items'][0].update(on_hold=False,settlement_status='pending')
            return copy.deepcopy(order['transfers']['items'][0])
        return copy.deepcopy(order)
    monkeypatch.setattr(payments.Razorpay,'request',request)
    with TestClient(main.app) as c:
        p=c.post('/api/session').json()['projects'][0]
        payload={'content_hash':p['hash'],'reviewed':True}
        path='/api/projects/'+p['id']
        c.post(path+'/approve',json=payload)
        c.post('/api/session/role',json={'role':'builder'})
        c.post(path+'/approve',json=payload)
        c.post('/api/session/role',json={'role':'client'})
        yield c,path,payload,order,calls

def fund(setup):
    c,path,payload,order,calls=setup
    response=c.post(path+'/payment/order',json=payload)
    assert response.status_code==200,response.text
    order.update(status='paid',amount_paid=order['amount'],amount_due=0)
    order['transfers']={'items':[{'id':'trf_fixture','source':'order_fixture','recipient':'acc_fixture','amount':order['amount'],'currency':'INR','status':'processed','on_hold':True,'on_hold_until':None,'settlement_status':'on_hold','amount_reversed':0}]}
    assert c.post(path+'/payment/refresh').json()['payment']['status']=='FUNDED'

def verified(setup):
    c,path,payload,*_=setup
    p=main.store.get('project#'+path.split('/')[-1])
    p.update(state='VERIFIED',delivery={'url':'https://example.com','at':'2026-09-20T00:00:00Z','hash':p['hash']})
    p['runs']=[{'id':'run_test','agreement_hash':p['hash'],'url':'https://example.com','at':'2026-09-20T01:00:00Z','results':[{'status':'passed'}]}]
    main.store.put('project#'+p['id'],p)

def test_disabled_and_live_keys_fail_closed(setup,monkeypatch):
    c,path,payload,*_=setup
    monkeypatch.setenv('RAZORPAY_KEY_ID','rzp_live_fixture')
    assert not c.get('/api/payments/config').json()['configured']
    assert c.post(path+'/payment/order',json=payload).status_code==503

def test_order_binds_amount_scope_and_hold_and_retries_reuse(setup):
    c,path,payload,order,calls=setup
    a=c.post(path+'/payment/order',json=payload).json()
    b=c.post(path+'/payment/order',json=payload).json()
    assert a['checkout']['order_id']==b['checkout']['order_id']
    assert len(calls)==1
    assert calls[0][2]['transfers'][0]['on_hold'] is True
    assert calls[0][2]['partial_payment'] is False
    assert calls[0][2]['notes']['agreement_hash']==payload['content_hash']
    assert 'recipient' not in a['project']['payment']
    c.post('/api/session/role',json={'role':'builder'})
    assert c.post(path+'/payment/order',json=payload).status_code==403

def test_order_requires_review_and_current_hash(setup):
    c,path,payload,order,calls=setup
    for body in [dict(payload,reviewed=False),dict(payload,content_hash='old')]:
        assert c.post(path+'/payment/order',json=body).status_code==409
    assert calls==[]

def test_foreign_sessions_and_forged_callback_cannot_fund(setup):
    c,path,payload,*_=setup
    c.post(path+'/payment/order',json=payload)
    with TestClient(main.app) as other:
        other.post('/api/session')
        assert other.post(path+'/payment/refresh').status_code==404
    assert c.post(path+'/payment/confirm',json={'razorpay_order_id':'order_fixture','razorpay_payment_id':'pay_fixture','razorpay_signature':'0'*64}).status_code==400
    signature=hmac.new(b'test-fixture-secret',b'order_fixture|pay_fixture',hashlib.sha256).hexdigest()
    p=c.post(path+'/payment/confirm',json={'razorpay_order_id':'order_fixture','razorpay_payment_id':'pay_fixture','razorpay_signature':signature}).json()
    assert p['payment']['status']=='AWAITING_PAYMENT' # even a signed callback is not captured funding

def test_wrong_recipient_or_amount_never_funds(setup):
    c,path,payload,order,calls=setup
    fund(setup)
    order['transfers']['items'][0]['recipient']='acc_attacker'
    assert c.post(path+'/payment/refresh').status_code==409
    verified(setup)
    assert c.post(path+'/payment/release',json=payload).status_code==409
    assert not any(m=='PATCH' for m,_,_ in calls)

def test_dispute_blocks_release_and_amendment(setup):
    c,path,payload,*_=setup
    fund(setup);verified(setup)
    c.post('/api/session/role',json={'role':'builder'})
    assert c.post(path+'/payment/dispute',json={'reason':'Client requested unpaid additional work.'}).json()['payment']['status']=='DISPUTED'
    assert c.post(path+'/payment/refresh').json()['payment']['status']=='DISPUTED'
    c.post('/api/session/role',json={'role':'client'})
    assert c.post(path+'/payment/release',json=payload).status_code==409
    assert c.post(path+'/amend',json={'included':['Extra work'],'price_minor':800000,'deadline':'2026-09-25'}).status_code==409

def test_release_requires_evidence_and_client_then_reports_pending(setup):
    c,path,payload,order,calls=setup
    fund(setup)
    assert c.post(path+'/payment/release',json=payload).status_code==409
    verified(setup)
    c.post('/api/session/role',json={'role':'builder'})
    assert c.post(path+'/payment/release',json=payload).status_code==403
    c.post('/api/session/role',json={'role':'client'})
    assert c.post(path+'/payment/release',json=payload).json()['payment']['status']=='RELEASE_PENDING'
    assert c.post(path+'/payment/release',json=payload).status_code==409
    assert sum(m=='PATCH' for m,_,_ in calls)==1
    order['transfers']['items'][0]['settlement_status']='settled'
    assert c.post(path+'/payment/refresh').json()['payment']['status']=='SETTLED'

def test_uncertain_creation_is_not_retried(setup,monkeypatch):
    c,path,payload,order,calls=setup
    def failed(*args,**kwargs): raise payments.HTTPException(502,'Uncertain')
    monkeypatch.setattr(payments.Razorpay,'create',failed)
    assert c.post(path+'/payment/order',json=payload).status_code==502
    assert c.post(path+'/payment/order',json=payload).status_code==409
    assert c.get(path).json()['payment']['status']=='CREATING'

def test_webhook_authentication_and_duplicate_events_use_provider_truth(setup,monkeypatch):
    import json
    c,path,payload,order,calls=setup
    fund(setup)
    monkeypatch.setenv('RAZORPAY_WEBHOOK_SECRET','webhook-fixture')
    body=json.dumps({'event':'payment.captured','payload':{'payment':{'entity':{'order_id':'order_fixture','amount':1}}}}).encode()
    assert c.post('/api/payments/webhook',content=body,headers={'x-razorpay-signature':'bad'}).status_code==400
    signature=hmac.new(b'webhook-fixture',body,hashlib.sha256).hexdigest()
    for _ in range(2):
        assert c.post('/api/payments/webhook',content=body,headers={'x-razorpay-signature':signature}).status_code==200
    assert c.get(path).json()['payment']['status']=='FUNDED'
    assert sum(m=='POST' for m,_,_ in calls)==1

def test_release_timeout_keeps_write_reserved(setup,monkeypatch):
    c,path,payload,*_=setup
    fund(setup);verified(setup)
    def failed(*args): raise payments.HTTPException(502,'Uncertain')
    monkeypatch.setattr(payments.Razorpay,'release',failed)
    assert c.post(path+'/payment/release',json=payload).status_code==502
    assert c.post(path+'/payment/release',json=payload).status_code==409
    assert c.post(path+'/payment/dispute',json={'reason':'A racing dispute must not claim a hold.'}).status_code==409
    assert c.get(path).json()['payment']['status']=='RELEASING'

def test_external_release_or_reversal_requires_review(setup):
    c,path,payload,order,*_=setup
    fund(setup)
    order['transfers']['items'][0].update(on_hold=False,settlement_status='pending')
    assert c.post(path+'/payment/refresh').json()['payment']['status']=='REVIEW_REQUIRED'
    order['transfers']['items'][0].update(on_hold=True,settlement_status='on_hold',amount_reversed=100)
    assert c.post(path+'/payment/refresh').json()['payment']['status']=='REVIEW_REQUIRED'

def test_pending_amendment_blocks_funding(setup):
    c,path,payload,order,calls=setup
    assert c.post(path+'/amend',json={'included':['Extra work'],'price_minor':800000,'deadline':'2026-09-25'}).status_code==200
    assert c.post(path+'/payment/order',json=payload).status_code==409
    assert calls==[]
