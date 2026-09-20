import json
import time
import pytest
from fastapi.testclient import TestClient
from backend import main
from backend.store import Store

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'store', Store(tmp_path/'a2a.sqlite'))
    with TestClient(main.app) as c: yield c

def setup(c, work=True):
    p=c.post('/api/session').json()['projects'][0]
    grant=c.post(f"/api/projects/{p['id']}/agent-access",json={'allow_work':work}).json()
    return p, grant

def rpc(c, token, method, params=None, version='1.0'):
    return c.post('/api/a2a',headers={'Authorization':'Bearer '+token,'A2A-Version':version},json={'jsonrpc':'2.0','id':'req','method':method,'params':params or {}})

def send(c, token, p, action='get_pact', mid='message-one', **kwargs):
    return rpc(c,token,'SendMessage',{'message':{'messageId':mid,'role':'ROLE_USER','contextId':p['id'],'parts':[{'data':{'action':action,**kwargs}}]}})

def test_card_and_authentication(client):
    card=client.get('/.well-known/agent-card.json').json()
    assert card['supportedInterfaces'][0]['protocolVersion']=='1.0'
    assert not card['capabilities']['streaming']
    assert card['securitySchemes']['pactKey']['httpAuthSecurityScheme']['scheme']=='Bearer'
    assert rpc(client,'invalid','ListTasks').status_code==401
    p,g=setup(client)
    assert rpc(client,g['token'],'ListTasks',version='0.3').json()['error']['code']==-32009
    assert rpc(client,g['token'],'SendStreamingMessage').json()['error']['code']==-32004
    assert rpc(client,g['token'],'CreateTaskPushNotificationConfig').json()['error']['code']==-32003

def test_task_read_replay_and_redaction(client):
    p,g=setup(client)
    first=send(client,g['token'],p).json()['result']['task']
    assert first['status']['state']=='TASK_STATE_COMPLETED'
    assert send(client,g['token'],p).json()['result']['task']==first
    serialized=json.dumps(first)
    for private in ('private_limit_minor','opening_minor','650000','800000','recipient','proofpact_session',g['token']):
        assert private not in serialized
    got=rpc(client,g['token'],'GetTask',{'id':first['id'],'historyLength':0}).json()['result']
    assert 'history' not in got
    assert got['artifacts'][0]['parts'][0]['data']['hash']==p['hash']
    assert rpc(client,g['token'],'CancelTask',{'id':first['id']}).json()['error']['code']==-32002
    changed=send(client,g['token'],p,action='negotiate',expected_hash=p['hash'])
    assert changed.json()['error']['code']==-32602

def test_list_pagination_and_isolation(client):
    p,g=setup(client)
    first=send(client,g['token'],p).json()['result']['task']
    send(client,g['token'],p,mid='second')
    page=rpc(client,g['token'],'ListTasks',{'pageSize':1}).json()['result']
    assert page['totalSize']==2 and page['nextPageToken']
    assert 'artifacts' not in page['tasks'][0] and 'history' not in page['tasks'][0]
    second=rpc(client,g['token'],'ListTasks',{'pageSize':1,'pageToken':page['nextPageToken'],'includeArtifacts':True}).json()['result']
    assert second['nextPageToken']=='' and second['tasks'][0]['id']!=page['tasks'][0]['id']
    with TestClient(main.app) as other:
        op,og=setup(other)
        assert rpc(other,og['token'],'GetTask',{'id':first['id']}).json()['error']['code']==-32001
        assert send(other,og['token'],p).json()['error']['code']==-32602
        assert other.post(f"/api/projects/{p['id']}/agent-access",json={}).status_code==404
    assert rpc(client,g['token'],'ListTasks',{'pageSize':True}).json()['error']['code']==-32602
    assert rpc(client,g['token'],'ListTasks',{'statusTimestampAfter':'not-a-time'}).json()['error']['code']==-32602

def test_readonly_rotation_revoke_and_expiry(client):
    p,g=setup(client,False)
    assert send(client,g['token'],p,'negotiate',expected_hash=p['hash']).json()['error']['code']==-32004
    newer=client.post(f"/api/projects/{p['id']}/agent-access",json={}).json()
    assert rpc(client,g['token'],'ListTasks').status_code==401
    assert rpc(client,newer['token'],'ListTasks').status_code==200
    client.delete(f"/api/projects/{p['id']}/agent-access")
    assert rpc(client,newer['token'],'ListTasks').status_code==401
    _,last=setup(client)
    key=f"a2a-access#{p['id']}#client"
    grant=main.store.get(key);grant['expires']=time.time()-1;main.store.put(key,grant)
    assert rpc(client,last['token'],'ListTasks').status_code==401

def test_role_does_not_follow_demo_switch_and_no_human_authority(client):
    p,g=setup(client)
    client.post('/api/session/role',json={'role':'builder'})
    assert send(client,g['token'],p,'submit_delivery',url='https://example.com',expected_hash=p['hash']).json()['error']['code']==-32004
    for action in ('approve','human_review','release','share','amend'):
        assert send(client,g['token'],p,action).json()['error']['code']==-32602
    # A bearer key never authenticates the ordinary human endpoints.
    with TestClient(main.app) as other:
        assert other.post(f"/api/projects/{p['id']}/approve",headers={'Authorization':'Bearer '+g['token']},json={'content_hash':p['hash'],'reviewed':True}).status_code==401

def test_negotiation_executes_once_and_requires_fresh_hash(client,monkeypatch):
    p,g=setup(client)
    assert send(client,g['token'],p,'negotiate',expected_hash='stale').json()['error']['code']==-32602
    calls=[]
    original=main.negotiate
    def tracked(*a): calls.append(1);return original(*a)
    monkeypatch.setattr(main,'negotiate',tracked)
    task=send(client,g['token'],p,'negotiate',expected_hash=p['hash']).json()['result']['task']
    assert task['status']['state']=='TASK_STATE_COMPLETED'
    result=task['artifacts'][0]['parts'][0]['data']
    assert result['state']=='AWAITING_APPROVAL' and result['approvals']=={}
    assert send(client,g['token'],p,'negotiate',expected_hash=p['hash']).json()['result']['task']==task
    assert len(calls)==1

def test_delivery_state_and_provider_failure(client,monkeypatch):
    p,g=setup(client)
    failed=send(client,g['token'],p,'verify_delivery',expected_hash=p['hash']).json()['result']['task']
    assert failed['status']['state']=='TASK_STATE_FAILED'
    assert send(client,g['token'],p,'verify_delivery',expected_hash=p['hash']).json()['result']['task']==failed
    def broken(*a): raise RuntimeError('SECRET provider response')
    monkeypatch.setattr(main,'negotiate',broken)
    task=send(client,g['token'],p,'negotiate',mid='failure',expected_hash=p['hash']).json()['result']['task']
    assert task['status']['state']=='TASK_STATE_FAILED' and 'SECRET' not in json.dumps(task)

def test_malformed_requests_and_unsupported_config(client):
    p,g=setup(client)
    headers={'Authorization':'Bearer '+g['token'],'A2A-Version':'1.0'}
    assert client.post('/api/a2a',headers=headers,content='{').json()['error']['code']==-32700
    assert client.post('/api/a2a',headers=headers,json=[]).json()['error']['code']==-32600
    assert client.post('/api/a2a',headers=headers,content='x'*65537).status_code==413
    params={'message':{'messageId':'m','role':'ROLE_USER','parts':[{'data':{'action':'get_pact'}}]},'configuration':{'returnImmediately':True}}
    assert rpc(client,g['token'],'SendMessage',params).json()['error']['code']==-32004
    params['configuration']={'taskPushNotificationConfig':{'url':'http://127.0.0.1'}}
    assert rpc(client,g['token'],'SendMessage',params).json()['error']['code']==-32003
    params['configuration']={};params['message']['parts'][0]['text']='ambiguous'
    assert rpc(client,g['token'],'SendMessage',params).json()['error']['code']==-32602

def test_concurrent_retry_cannot_duplicate_work(client,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    p,g=setup(client)
    entered,release=Event(),Event()
    calls=[]
    original=main.negotiate
    def slow(*args):
        calls.append(1);entered.set()
        assert release.wait(5)
        return original(*args)
    monkeypatch.setattr(main,'negotiate',slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending=pool.submit(send,client,g['token'],p,'negotiate',expected_hash=p['hash'])
        assert entered.wait(3)
        try:
            duplicate=send(client,g['token'],p,'negotiate',expected_hash=p['hash']).json()
            assert duplicate['error']['code']==-32004
            tasks=rpc(client,g['token'],'ListTasks',{}).json()['result']['tasks']
            assert tasks[0]['status']['state']=='TASK_STATE_WORKING'
        finally: release.set()
        assert pending.result().json()['result']['task']['status']['state']=='TASK_STATE_COMPLETED'
    assert len(calls)==1

def test_hash_guard_rechecked_inside_operation(client,monkeypatch):
    p,g=setup(client)
    original=main.start_negotiation
    def race(pid,body,grant):
        current=main.store.get('project#'+pid)
        current['hash']='changed-concurrently'
        main.store.put('project#'+pid,current)
        return original(pid,body,grant)
    monkeypatch.setattr(main,'start_negotiation',race)
    task=send(client,g['token'],p,'negotiate',expected_hash=p['hash']).json()['result']['task']
    assert task['status']['state']=='TASK_STATE_FAILED'
    assert 'agreement changed' in task['status']['message']['parts'][0]['text']
    assert len(main.store.get('project#'+p['id'])['proposals'])==3
