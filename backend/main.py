import hashlib
import os
import secrets
import time
from typing import Literal
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from .store import make_store, Conflict
from .domain import create_project,seed_proposals,public_project,event,digest,now,uid,finish_state
from .agents import negotiate
from .verifier import run_verification,safe_target,DATA
from .fixture import fixture_html

app=FastAPI(title='ProofPact API',version='0.1.0')
store=make_store()
DEMO=os.getenv('DEMO_MODE','true')=='true'

@app.exception_handler(Conflict)
async def conflict_handler(request,exc): return JSONResponse(status_code=409,content={'detail':str(exc)})

@app.middleware('http')
async def security(request,call_next):
    if request.method not in ('GET','HEAD','OPTIONS'):
        origin=request.headers.get('origin')
        expected=os.getenv('PUBLIC_ORIGIN','http://127.0.0.1:3000')
        allowed_origins = {expected}
        if expected == 'http://127.0.0.1:3000': allowed_origins.add('http://localhost:3000')
        if origin and origin not in allowed_origins:
            return JSONResponse(status_code=403,content={'detail':'Request origin is not allowed.'})
        try: content_length = int(request.headers.get('content-length','0'))
        except ValueError: return JSONResponse(status_code=400,content={'detail':'Invalid content length.'})
        if content_length>65536 or len(await request.body())>65536:
            return JSONResponse(status_code=413,content={'detail':'Request is too large.'})
    result=await call_next(request)
    result.headers['X-Content-Type-Options']='nosniff'
    result.headers['Referrer-Policy']='same-origin'
    if request.url.path.startswith('/api/'): result.headers['Cache-Control']='no-store'
    return result

def session(request:Request):
    token=request.cookies.get('proofpact_session','')
    s=store.get('session#'+hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not s or s['expires']<time.time(): raise HTTPException(401,'Session expired. Sign in again or open Demo Theater.')
    if s.get('type')=='account':
        user=store.get('user#'+s['user_id'])
        if not user or user['epoch']!=s.get('auth_epoch'): raise HTTPException(401,'Sign in again.')
    return s

def save_session(s): store.put('session#'+s['key'],s)
def project(pid,s):
    p=store.get('project#'+pid)
    if not p: raise HTTPException(404,'Pact not found.')
    if p.get('identity_mode')=='account':
        user=store.get('user#'+s.get('user_id',''))
        if s.get('type')!='account' or p.get('members',{}).get(s['role'])!=s.get('user_id') or not user or user['epoch']!=s.get('auth_epoch'): raise HTTPException(404,'Pact not found.')
    elif s.get('type')=='account' or p['owner']!=s['workspace']: raise HTTPException(404,'Pact not found.')
    if s.get('agent_expected_hash') and s['agent_expected_hash']!=(p.get('hash') or 'unversioned'):
        raise HTTPException(409,'The agreement changed. Refresh it before requesting more work.')
    return p

def save(p): return public_project(store.put('project#'+p['id'],p))
def role(s,wanted):
    if s['role']!=wanted: raise HTTPException(403,f'Only the {wanted} can do this.')
def state(p,allowed):
    if p['state'] not in allowed: raise HTTPException(409,'This action is not available in the current pact state.')
def consume(s,kind,limit):
    key=f"quota#{s['workspace']}#{kind}#{time.strftime('%Y-%m-%d',time.gmtime())}"
    q=store.get(key) or {'count':0}
    if q['count']>=limit: raise HTTPException(429,'Daily demo limit reached. Try again tomorrow.')
    q['count']+=1;store.put(key,q)
    global_key=f"global-quota#{kind}#{time.strftime('%Y-%m-%d',time.gmtime())}"
    g=store.get(global_key) or {'count':0}
    if g['count']>=100: raise HTTPException(429,'The public demo has reached its daily limit.')
    g['count']+=1;store.put(global_key,g)

@app.get('/api/health')
def health(): return {'status':'ok','storage':'dynamodb' if os.getenv('DYNAMODB_TABLE') else 'sqlite','agent_provider':os.getenv('AGENT_PROVIDER','demo'),'demo':DEMO}

@app.post('/api/session')
def bootstrap(request:Request,response:Response):
    if not DEMO: raise HTTPException(403,'Demo sessions are disabled. Production authentication must be configured.')
    try: s=session(request)
    except HTTPException:
        token=secrets.token_urlsafe(32);key=hashlib.sha256(token.encode()).hexdigest()
        s=store.put('session#'+key,{'key':key,'workspace':uid('ws'),'role':'client','expires':time.time()+86400,'projects':[]})
        response.set_cookie('proofpact_session',token,httponly=True,samesite='lax',secure=os.getenv('COOKIE_SECURE','false')=='true',max_age=86400)
    if s.get('type')=='account': return current_session(s)
    if not s['projects']:
        p=create_project('Acme Admin Portal','Build an admin dashboard with login, analytics, CSV export, OTP, dark mode and payments by Sunday for ₹5,000.',fixture=True)
        p['owner']=s['workspace'];p['brief_ready']={'client':True,'builder':True};seed_proposals(p);save(p)
        for r,b in [('client',{'private_limit_minor':800000,'opening_minor':500000,'deadline':'2026-09-23','notes':'Keep OTP; payments can wait.'}),('builder',{'private_limit_minor':650000,'opening_minor':800000,'deadline':'2026-09-21','notes':'Payments require additional security work.'})]:
            store.put(f"brief#{p['id']}#{r}",b)
        s['projects'].append(p['id']);save_session(s)
    return {'role':s['role'],'projects':[public_project(project(pid,s)) for pid in s['projects']],'demo':True,'agent_provider':os.getenv('AGENT_PROVIDER','demo')}


@app.get('/api/session')
def current_session(s=Depends(session)):
    user=store.get('user#'+s['user_id']) if s.get('type')=='account' else None
    ids=user['projects'] if user else s['projects']
    return {'role':s['role'],'name':s.get('name'),'projects':[public_project(project(pid,s)) for pid in ids], 'demo':not bool(user),'agent_provider':os.getenv('AGENT_PROVIDER','demo')}

class RoleBody(BaseModel): role:Literal['client','builder']
@app.post('/api/session/role')
def switch(body:RoleBody,s=Depends(session)):
    if not DEMO or s.get('type')=='account': raise HTTPException(403,'Role switching is only available in Demo Theater.')
    s['role']=body.role;save_session(s);return {'role':s['role']}

class ProjectBody(BaseModel):
    name:str=Field(min_length=3,max_length=100)
    brief:str=Field(min_length=10,max_length=4000)
    client:str=Field(min_length=1,max_length=80)
    builder:str=Field(min_length=1,max_length=80)
    requirements:list[str]=Field(min_length=1,max_length=20)
    acceptance_criteria:list[str]=Field(default_factory=list,max_length=20)
    revision_days:int=Field(default=7,ge=1,le=30)
@app.post('/api/projects')
def create(body:ProjectBody,s=Depends(session)):
    consume(s,'projects',10)
    if any(not x.strip() or len(x)>200 for x in body.requirements): raise HTTPException(422,'Each requirement must be 1–200 characters.')
    if any(not x.strip() or len(x)>500 for x in body.acceptance_criteria): raise HTTPException(422,'Acceptance criteria must be 1–500 characters.')
    if s.get('type')=='account' and not body.acceptance_criteria: raise HTTPException(422,'Define observable acceptance criteria before creating this pact.')
    p=create_project(**body.model_dump());p['owner']=s['workspace']
    if s.get('type')=='account':
        p['identity_mode']='account';p['members']={'client':None,'builder':None};p['members'][s['role']]=s['user_id'];p[s['role']]=s['name']
    save(p)
    if s.get('type')=='account':
        from .auth import add_project
        add_project(store,s['user_id'],p['id'])
    else: s['projects'].append(p['id']);save_session(s)
    return public_project(p)
@app.get('/api/projects/{pid}')
def get_project(pid:str,s=Depends(session)): return public_project(project(pid,s))

class BriefBody(BaseModel):
    private_limit_minor:int=Field(ge=100,le=1000000000)
    opening_minor:int=Field(ge=100,le=1000000000)
    deadline:str=Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    notes:str=Field(default='',max_length=2000)
@app.get('/api/projects/{pid}/brief')
def get_brief(pid:str,s=Depends(session)):
    project(pid,s);b=store.get(f"brief#{pid}#{s['role']}")
    return {k:v for k,v in b.items() if k!='_rev'} if b else None
@app.put('/api/projects/{pid}/brief')
def put_brief(pid:str,body:BriefBody,s=Depends(session)):
    from datetime import date
    try: date.fromisoformat(body.deadline)
    except ValueError: raise HTTPException(422,'Enter a valid date.')
    p=project(pid,s);state(p,['BRIEFING','NO_DEAL'])
    key=f"brief#{pid}#{s['role']}";old=store.get(key) or {}
    store.put(key,{**old,**body.model_dump()});p['brief_ready'][s['role']]=True
    event(p,s['role'],'Private brief saved','Constraints are only available to this participant and their advocate.')
    if all(p['brief_ready'].values()): p['state']='READY_TO_NEGOTIATE'
    return save(p)

class NegotiateBody(BaseModel): mode:Literal['demo','bedrock','modal']='demo'
@app.post('/api/projects/{pid}/negotiate')
def start_negotiation(pid:str,body:NegotiateBody,s=Depends(session)):
    p=project(pid,s);state(p,['READY_TO_NEGOTIATE','AWAITING_APPROVAL','NO_DEAL'])
    if p.get('identity_mode')=='account' and not all(p['members'].values()): raise HTTPException(409,'Both participants must join before negotiation.')
    if not all(p['brief_ready'].values()): raise HTTPException(409,'Both private briefs are required.')
    if len(p['proposals'])>=10: raise HTTPException(429,'This demo pact has reached its proposal limit.')
    consume(s,'negotiation',10)
    previous=p['state'];p['state']='NEGOTIATING';p=store.put('project#'+pid,p)
    try: negotiate(p,store.get(f'brief#{pid}#client'),store.get(f'brief#{pid}#builder'),body.mode)
    except Exception:
        p['state']=previous;save(p)
        raise HTTPException(503,'The model provider could not complete negotiation. Your agreement is unchanged. Retry or use the labeled sample mode.')
    return save(p)

class ApproveBody(BaseModel):
    content_hash:str
    reviewed:bool
@app.post('/api/projects/{pid}/approve')
def approve(pid:str,body:ApproveBody,s=Depends(session)):
    p=project(pid,s);state(p,['AWAITING_APPROVAL'])
    if not body.reviewed: raise HTTPException(422,'Confirm you reviewed this version.')
    if body.content_hash!=p['hash'] or digest(p['current'])!=p['hash']: raise HTTPException(409,'The agreement changed. Review the latest version.')
    p['approvals'][s['role']]={'role':s['role'],'hash':p['hash'],'at':now(),'identity':'verified_account' if s.get('type')=='account' else 'demo'}
    event(p,s['role'],f"{s['role'].title()} approved v{p['current']['version']}",'Human approval recorded for this exact agreement hash.')
    if set(p['approvals'])=={'client','builder'} and all(a['hash']==p['hash'] for a in p['approvals'].values()):
        p['state']='AGREEMENT_LOCKED';p['agreements'].append({'agreement':p['current'],'hash':p['hash'],'approvals':p['approvals'].copy(),'at':now()})
        event(p,'system','Agreement locked','Both people approved the same version. The scope is now immutable.')
    return save(p)

class ChangeBody(BaseModel): text:str=Field(min_length=5,max_length=2000)
@app.post('/api/projects/{pid}/changes')
def change(pid:str,body:ChangeBody,s=Depends(session)):
    role(s,'client');p=project(pid,s);state(p,['AGREEMENT_LOCKED','SUBMITTED','NEEDS_FIX','NEEDS_HUMAN_REVIEW','VERIFIED'])
    request=body.text.lower()
    excluded=[x for x in p['current']['excluded'] if any(word in request for word in x.lower().split() if len(word)>3)]
    included=[x for x in p['current']['included'] if x.lower() in request]
    category='scope_change' if excluded else 'clarification' if included and request.startswith('clarify ') else 'ambiguous'
    c={'id':uid('change'),'text':body.text,'classification':category,'rationale':('This request touches explicitly excluded scope: '+', '.join(excluded)+'.') if excluded else 'This clarification references included scope.' if category=='clarification' else 'The request needs human review before its scope impact can be decided.','options':['Replace an existing deliverable','Extend the deadline and propose a new price','Keep the current agreement'],'at':now(),'status':'open'}
    p['changes'].append(c);event(p,'mediator','Change request reviewed',c['rationale']);return save(p)

class AmendmentBody(BaseModel):
    acceptance_criteria:list[str]|None=Field(default=None,min_length=1,max_length=20)
    revision_days:int|None=Field(default=None,ge=1,le=30)
    included:list[str]=Field(min_length=1,max_length=20)
    price_minor:int=Field(ge=100,le=1000000000)
    deadline:str=Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
@app.post('/api/projects/{pid}/amend')
def amend(pid:str,body:AmendmentBody,s=Depends(session)):
    from datetime import date
    try: date.fromisoformat(body.deadline)
    except ValueError: raise HTTPException(422,'Enter a valid date.')
    p=project(pid,s);state(p,['AGREEMENT_LOCKED','SUBMITTED','NEEDS_FIX','NEEDS_HUMAN_REVIEW','VERIFIED'])
    if any(not x.strip() or len(x)>200 for x in body.included): raise HTTPException(422,'Invalid scope item.')
    if p.get('payment'): raise HTTPException(409,'This milestone has a payment record. Resolve it before changing the funded agreement.')
    import copy
    a=copy.deepcopy(p['current']);a.update(version=a['version']+1,included=body.included,price_minor=body.price_minor,deadline=body.deadline)
    if body.acceptance_criteria and any(not x.strip() or len(x)>500 for x in body.acceptance_criteria): raise HTTPException(422,'Invalid acceptance criterion.')
    if body.revision_days is not None:
        a['revision_policy']={'days':body.revision_days,'starts':'first_delivery_submission','scope':'Corrections to agreed acceptance criteria; new features require an amendment.','expiry_effect':'No automatic acceptance or payment release.'}
    a['delivery_approver']={'role':'client','name':p['client']}
    a['criteria']=[{'id':f'amend-{i}','title':r,'description':f'Client reviews delivery of: {r}','method':'Human review','required':True} for i,r in enumerate(body.acceptance_criteria or body.included)]
    a['excluded']=[x for x in a['excluded'] if x not in body.included]
    if p.get('pending_amendment'): raise HTTPException(409,'Accept or reject the pending amendment first.')
    p['pending_amendment']={'agreement':a,'hash':digest(a),'base_hash':p['hash'],'approvals':{},'proposed_by':s['role'],'at':now()}
    event(p,s['role'],'Amendment proposed','The active agreement and delivery checks are unchanged until both people approve.');return save(p)

@app.post('/api/projects/{pid}/amendment/approve')
def approve_amendment(pid:str,body:ApproveBody,s=Depends(session)):
    p=project(pid,s);state(p,['AGREEMENT_LOCKED','SUBMITTED','NEEDS_FIX','NEEDS_HUMAN_REVIEW','VERIFIED'])
    if p.get('payment'): raise HTTPException(409,'Resolve the milestone payment before activating an amendment.')
    pending=p.get('pending_amendment')
    if not pending or pending['base_hash']!=p['hash']: raise HTTPException(409,'No current amendment is available.')
    if not body.reviewed: raise HTTPException(422,'Confirm you reviewed this amendment.')
    if body.content_hash!=pending['hash'] or digest(pending['agreement'])!=pending['hash']: raise HTTPException(409,'The amendment changed. Review it again.')
    pending['approvals'][s['role']]={'role':s['role'],'hash':pending['hash'],'at':now()}
    event(p,s['role'],'Amendment approval recorded','The active agreement remains in force until both people accept.')
    if set(pending['approvals'])=={'client','builder'}:
        a=pending['agreement']
        p.update(current=a,hash=pending['hash'],approvals=pending['approvals'],state='AGREEMENT_LOCKED',delivery=None,share_token=None)
        p['requirements']=a['included']
        p['agreements'].append({'agreement':a,'hash':p['hash'],'approvals':p['approvals'].copy(),'at':now()})
        p['proposals'].append({'agreement':a,'actor':pending['proposed_by'],'rationale':'Amendment accepted by both participants.','source':'human','at':now()})
        p['pending_amendment']=None
        p.pop('first_delivery_at',None)
        event(p,'system','Amendment activated','Both people accepted the same version. New delivery evidence is required.')
    return save(p)

@app.post('/api/projects/{pid}/amendment/reject')
def reject_amendment(pid:str,body:ApproveBody,s=Depends(session)):
    p=project(pid,s);pending=p.get('pending_amendment')
    if not pending or pending['hash']!=body.content_hash: raise HTTPException(409,'The amendment changed. Refresh and retry.')
    event(p,s['role'],'Amendment rejected','The previously agreed scope, delivery and approvals remain unchanged.')
    p['pending_amendment']=None
    return save(p)

class DeliveryBody(BaseModel): url:str=Field(max_length=2000);notes:str=Field(default='',max_length=2000)
@app.post('/api/projects/{pid}/delivery')
def deliver(pid:str,body:DeliveryBody,s=Depends(session)):
    role(s,'builder');p=project(pid,s);state(p,['AGREEMENT_LOCKED','SUBMITTED','NEEDS_FIX','NEEDS_HUMAN_REVIEW','VERIFIED'])
    if p.get('payment') and p['payment']['status'] != 'FUNDED': raise HTTPException(409,'The milestone must be confirmed funded and undisputed before delivery.')
    try: safe_target(body.url)
    except (ValueError,OSError) as e: raise HTTPException(422,str(e))
    p.setdefault('first_delivery_at',now())
    p['delivery']={**body.model_dump(),'at':now(),'hash':p['hash']};p['state']='SUBMITTED';p['share_token']=None
    event(p,'builder','Delivery submitted','Ready to verify against the locked criteria.');return save(p)
@app.post('/api/projects/{pid}/verify')
def verify(pid:str,s=Depends(session)):
    p=project(pid,s);state(p,['SUBMITTED','NEEDS_FIX','NEEDS_HUMAN_REVIEW'])
    consume(s,'verification',20)
    p['state']='VERIFYING';p=store.put('project#'+pid,p)
    from .evidence_store import archive
    try:
        run=run_verification(p)
        archive(run)
    except Exception:
        p['state']='SUBMITTED';save(p)
        raise HTTPException(503,'Evidence could not be archived. No verification was certified; please retry.')
    p['runs'].append(run);finish_state(p)
    event(p,'verifier','Verification completed',f"{sum(r['status']=='passed' for r in run['results'])} passed; evidence captured for agreement v{run['version']}.")
    return save(p)
class ConfirmBody(BaseModel): criterion_id:str;accepted:bool
@app.post('/api/projects/{pid}/human-review')
def human_review(pid:str,body:ConfirmBody,s=Depends(session)):
    role(s,'client');p=project(pid,s);state(p,['NEEDS_FIX','NEEDS_HUMAN_REVIEW'])
    result=next((r for r in p['runs'][-1]['results'] if r['criterion_id']==body.criterion_id),None)
    if not result or result['status']!='review': raise HTTPException(409,'This criterion is not awaiting human review.')
    result.update(status='passed' if body.accepted else 'failed',human_review={'role':'client','at':now(),'accepted':body.accepted})
    finish_state(p);event(p,'client','Human review recorded',result['title']);return save(p)
@app.get('/api/projects/{pid}/evidence/{filename}')
def evidence(pid:str,filename:str,s=Depends(session)):
    p=project(pid,s)
    if not any(e.get('name')==filename and e['type']=='screenshot' for run in p['runs'] for r in run['results'] for e in r['evidence']): raise HTTPException(404,'Evidence not found.')
    from .evidence_store import fetch
    if os.getenv('EVIDENCE_BUCKET'):
        try: return Response(content=fetch(filename),media_type='image/png')
        except Exception: raise HTTPException(503,'Evidence storage is temporarily unavailable.')
    path=DATA/filename
    if not path.is_file(): raise HTTPException(404,'Evidence file unavailable.')
    return FileResponse(path,media_type='image/png')
@app.post('/api/projects/{pid}/share')
def share(pid:str,s=Depends(session)):
    p=project(pid,s);state(p,['VERIFIED'])
    token=secrets.token_urlsafe(24)
    receipt={'project':p['name'],'agreement':p['current'],'hash':p['hash'],'approvals':p['approvals'],'run':p['runs'][-1],'issued_at':now()}
    # Public receipts carry observations and hashes, never raw screenshots, CSVs or private briefs.
    import copy
    receipt=copy.deepcopy(receipt)
    for r in receipt['run']['results']: r['evidence']=[]
    store.put('receipt#'+token,receipt);return {'token':token}
@app.get('/api/receipts/{token}')
def receipt(token:str):
    item=store.get('receipt#'+token)
    if not item: raise HTTPException(404,'Receipt not found.')
    return {k:v for k,v in item.items() if k!='_rev'}
@app.get('/fixture/{version}')
def fixture(version:str):
    if not DEMO or version not in ('broken','fixed'): raise HTTPException(404)
    return fixture_html(version=='fixed')

from .payments import install as install_payments
install_payments(app, lambda: store, session, project, role, consume)

# The protocol adapter delegates only these operations. Approval, human review,
# receipt publication and every payment endpoint are deliberately absent.
from .a2a import install as install_a2a

def execute_agent_command(command, grant):
    p=project(grant['project_id'],grant)
    if command.action!='get_pact' and command.expected_hash!=(p.get('hash') or 'unversioned'):
        raise HTTPException(409,'The agreement changed. Refresh it before requesting more work.')
    pid=p['id']
    if command.action!='get_pact': grant={**grant,'agent_expected_hash':command.expected_hash}
    if command.action=='get_pact': return p
    if command.action=='negotiate':
        return start_negotiation(pid,NegotiateBody(mode=command.mode),grant)
    if command.action=='check_change':
        return change(pid,ChangeBody(text=command.text),grant)
    if command.action=='submit_delivery':
        return deliver(pid,DeliveryBody(url=command.url,notes=command.notes),grant)
    if command.action=='verify_delivery': return verify(pid,grant)
    raise HTTPException(403,'Agent action is not allowed.')

install_a2a(app,lambda:store,session,project,consume,execute_agent_command)

from .auth import install as install_auth
install_auth(app,lambda:store,session,project,consume)

class RevisionBody(BaseModel):
    criterion_ids:list[str]=Field(min_length=1,max_length=20)
    notes:str=Field(min_length=5,max_length=2000)
@app.post('/api/projects/{pid}/revisions')
def revision(pid:str,body:RevisionBody,s=Depends(session)):
    from datetime import datetime,timedelta,timezone
    role(s,'client');p=project(pid,s)
    state(p,['SUBMITTED','NEEDS_FIX','NEEDS_HUMAN_REVIEW','VERIFIED'])
    first=p.get('first_delivery_at')
    policy=p['current'].get('revision_policy')
    if not first or not policy: raise HTTPException(409,'This agreement has no active revision window. Propose an amendment.')
    end=datetime.fromisoformat(first)+timedelta(days=policy['days'])
    if datetime.now(timezone.utc)>end: raise HTTPException(409,'The agreed revision window has ended. Propose a mutually accepted amendment.')
    ids={c['id'] for c in p['current']['criteria']}
    if not set(body.criterion_ids)<=ids: raise HTTPException(422,'Revisions must reference agreed acceptance criteria.')
    consume(s,'revisions',20)
    p.setdefault('revisions',[]).append({**body.model_dump(),'id':uid('revision'),'hash':p['hash'],'at':now(),'requested_by':'client'})
    p['state']='NEEDS_FIX'
    event(p,'client','Revision requested','Corrections requested within the agreed window. Scope and price remain unchanged.')
    return save(p)
