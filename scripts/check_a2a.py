"""A synthetic client through the public A2A HTTP binding; never prints bearer keys."""
import json
import sys
import uuid
import httpx

base = sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'http://127.0.0.1:8000'
with httpx.Client(base_url=base,timeout=180) as c:
    def post(path, body=None):
        r=c.post('/api'+path,json=body);r.raise_for_status();return r.json()
    card=c.get('/.well-known/agent-card.json');card.raise_for_status()
    assert card.json()['supportedInterfaces'][0]['protocolVersion']=='1.0'
    p=post('/session')['projects'][0];path='/projects/'+p['id']
    grants=[]
    def grant():
        key=post(path+'/agent-access',{'allow_work':True})['token'];grants.append(key);return key
    def rpc(key,method,params):
        r=c.post('/api/a2a',headers={'Authorization':'Bearer '+key,'A2A-Version':'1.0'},json={'jsonrpc':'2.0','id':str(uuid.uuid4()),'method':method,'params':params})
        r.raise_for_status();data=r.json();assert 'error' not in data,data;return data['result']
    def send(key,action,**fields):
        message={'messageId':str(uuid.uuid4()),'role':'ROLE_USER','contextId':p['id'],'parts':[{'data':{'action':action,**fields}}]}
        task=rpc(key,'SendMessage',{'message':message})['task']
        assert task['status']['state']=='TASK_STATE_COMPLETED',task['status']
        replay=rpc(key,'SendMessage',{'message':message})['task'];assert replay==task
        assert rpc(key,'GetTask',{'id':task['id']})['id']==task['id']
        return task['artifacts'][0]['parts'][0]['data']
    client_key=grant()
    try:
        proposal=send(client_key,'negotiate',expected_hash=p['hash'],mode='demo')
        h=proposal['hash'];assert proposal['approvals']=={} and proposal['state']=='AWAITING_APPROVAL'
        post(path+'/approve',{'content_hash':h,'reviewed':True})
        post('/session/role',{'role':'builder'})
        assert post(path+'/approve',{'content_hash':h,'reviewed':True})['state']=='AGREEMENT_LOCKED'
        builder_key=grant()
        for fixture,expected in [('broken','NEEDS_FIX'),('fixed','NEEDS_HUMAN_REVIEW')]:
            delivery=send(builder_key,'submit_delivery',expected_hash=h,url='http://127.0.0.1:8000/fixture/'+fixture)
            assert delivery['state']=='SUBMITTED'
            verified=send(client_key,'verify_delivery',expected_hash=h)
            assert verified['state']==expected
            assert all('evidence' not in row for row in verified['verification']['results'])
        assert rpc(builder_key,'ListTasks',{'includeArtifacts':False})['totalSize']==2
        assert rpc(client_key,'ListTasks',{})['totalSize']==3
        print(json.dumps({'a2a_version':'1.0','sample_negotiation':True,'delivery_checks':['NEEDS_FIX','NEEDS_HUMAN_REVIEW'],'idempotent_replays':True,'human_review_still_required':True,'keys_printed':False}))
    finally:
        for role in ('client','builder'):
            post('/session/role',{'role':role})
            r=c.delete('/api'+path+'/agent-access');r.raise_for_status()
        for key in grants:
            assert c.post('/api/a2a',headers={'Authorization':'Bearer '+key},json={}).status_code==401
