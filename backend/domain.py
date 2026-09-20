import hashlib
import json
import uuid
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()
def uid(prefix): return f'{prefix}_{uuid.uuid4().hex[:16]}'
def digest(agreement):
    return hashlib.sha256(json.dumps(agreement, sort_keys=True, separators=(',', ':'),ensure_ascii=False).encode()).hexdigest()

def event(p, actor, title, detail=''):
    p['events'].append({'id':uid('evt'),'actor':actor,'title':title,'detail':detail,'at':now()})

CRITERIA = [
 {'id':'login','title':'Secure login','description':'Valid demo credentials open the dashboard.','method':'Browser assertion','required':True},
 {'id':'analytics','title':'Analytics overview','description':'Total orders and revenue are visible after login.','method':'DOM assertion','required':True},
 {'id':'otp','title':'OTP verification','description':'The seeded verification code completes the second factor.','method':'Browser assertion','required':True},
 {'id':'csv','title':'Complete CSV export','description':'Export includes all 27 records, across every page.','method':'Downloaded file analysis','required':True},
 {'id':'responsive','title':'Mobile layout','description':'At 390px there is no horizontal overflow. Client confirms visual usability.','method':'Browser + human review','required':True},
]

def agreement(p,price=750000,deadline='2026-09-21',version=3):
    requirements=p.get('requirements',['Secure login','Analytics dashboard','CSV export','OTP verification'])
    # Custom scope receives honest manual criteria until a supported test contract is configured.
    criteria=CRITERIA if p.get('fixture') else [{'id':f'custom-{i}','title':r,'description':f'Client reviews delivery of: {r}', 'method':'Human review','required':True} for i,r in enumerate(requirements)]
    return {'version':version,'project_id':p['id'],'name':p['name'],'client':p['client'],'builder':p['builder'],'currency':'INR','price_minor':price,'deadline':deadline,'included':requirements,'excluded':['Payment integration','Dark mode'] if p.get('fixture') else [],'criteria':criteria,'change_policy':'Changes require a new version and approval from both people. The current agreement stays locked.','risks':['Third-party service access must be supplied before delivery.']}

def create_project(name,brief,client='Alex Morgan',builder='Jamie Chen',fixture=False,requirements=None):
    p={'id':uid('p'),'name':name,'brief':brief,'client':client,'builder':builder,'fixture':fixture,'requirements':requirements or ['Secure login','Analytics dashboard','CSV export','OTP verification'],'state':'BRIEFING','created_at':now(),'events':[],'proposals':[],'agreements':[],'approvals':{},'changes':[],'runs':[],'delivery':None,'brief_ready':{'client':False,'builder':False},'share_token':None}
    event(p,'system','Pact created','A shared starting point. Private limits stay with each advocate.')
    return p

def seed_proposals(p):
    for version, price, date, actor, title, detail in [
      (1,500000,'2026-09-20','client','The opening brief','Login, analytics, export, OTP, payments and dark mode by Sunday.'),
      (2,800000,'2026-09-21','builder','A more realistic scope','Move payments and dark mode out of scope; allow one more day for OTP testing.'),
      (3,750000,'2026-09-21','mediator','A balanced proposal','Keep the four essentials. Meet at ₹7,500 with delivery on Monday.')]:
        a=agreement(p,price,date,version)
        if version==1: a['included']=a['included']+a['excluded'];a['excluded']=[]
        p['proposals'].append({'agreement':a,'actor':actor,'rationale':detail,'source':'demo','at':now()})
        event(p,actor,title,detail)
    p['current']=p['proposals'][-1]['agreement'];p['hash']=digest(p['current']);p['state']='AWAITING_APPROVAL'

def public_project(p):
    result = {k:v for k,v in p.items() if k not in ('_rev','share_token','owner','operation')}
    if result.get('payment'):
        result['payment'] = {k:v for k,v in result['payment'].items() if k not in ('recipient','operation')}
    return result

def finish_state(p):
    results=p['runs'][-1]['results']
    if any(r['status'] in ('failed','blocked') for r in results): p['state']='NEEDS_FIX'
    elif any(r['status']=='review' for r in results): p['state']='NEEDS_HUMAN_REVIEW'
    else: p['state']='VERIFIED'
