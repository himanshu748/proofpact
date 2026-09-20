"""Cognito verifies identities; opaque server-side sessions authorize pact membership."""
import hashlib
import os
import secrets
import time
import uuid
from typing import Literal
from fastapi import Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from botocore.exceptions import ClientError
from .store import Conflict
from .domain import now, event

class Identity(BaseModel):
    email: str = Field(pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$', max_length=254)
class Login(Identity):
    password: str = Field(min_length=1, max_length=256)
    role: Literal['client','builder']
class Register(Login):
    name: str = Field(min_length=2,max_length=80)
class Confirmation(Identity):
    code: str = Field(min_length=4,max_length=16)
class Reset(Confirmation):
    password: str = Field(min_length=12,max_length=256)
class Invitation(BaseModel):
    token: str = Field(min_length=20,max_length=100)

def cognito():
    import boto3
    if not os.getenv('COGNITO_CLIENT_ID'): raise HTTPException(503,'Account sign-in is not configured yet.')
    return boto3.client('cognito-idp',region_name=os.getenv('AWS_REGION','us-east-1'))

def provider(method,**kwargs):
    try: return getattr(cognito(),method)(**kwargs)
    except ClientError as e:
        code=e.response['Error']['Code']
        if code=='UserNotConfirmedException': raise HTTPException(403,'Verify your email before signing in.')
        if code in ('TooManyRequestsException','LimitExceededException'): raise HTTPException(429,'Too many attempts. Please wait before trying again.')
        if code in ('CodeMismatchException','ExpiredCodeException'): raise HTTPException(400,'That verification code is incorrect or expired.')
        if code=='InvalidPasswordException': raise HTTPException(400,'Use at least 12 characters including uppercase, lowercase, a number and a symbol.')
        raise HTTPException(400,'The request could not be completed. Check your details or use password recovery.')

def client_id(): return os.getenv('COGNITO_CLIENT_ID','')
def email_key(email): return 'identity-email#'+hashlib.sha256(email.lower().strip().encode()).hexdigest()

def add_project(store, user_id, pid):
    for _ in range(5):
        user=store.get('user#'+user_id)
        if not user: raise HTTPException(409,'Participant account is unavailable.')
        if pid in user['projects']: return
        user['projects'].append(pid)
        try: store.put('user#'+user_id,user);return
        except Conflict: continue
    raise HTTPException(409,'Workspace changed. Please retry.')

def install(app,get_store,session,project,consume):
    def throttle(request,email):
        # Bound unauthenticated requests per address and globally. Cognito also throttles.
        identity=hashlib.sha256(email.lower().strip().encode()).hexdigest()
        consume({'workspace':'auth-'+identity},'identity',30)

    @app.get('/api/auth/config')
    def config(): return {'configured':bool(client_id()),'provider':'cognito'}

    @app.post('/api/auth/register')
    def register(body:Register,request:Request):
        throttle(request,body.email)
        if len(body.password)<12: raise HTTPException(422,'Use a password of at least 12 characters.')
        provider('sign_up',ClientId=client_id(),Username=body.email.lower().strip(),Password=body.password,
                 UserAttributes=[{'Name':'email','Value':body.email.lower().strip()},{'Name':'name','Value':body.name.strip()},{'Name':'custom:role','Value':body.role}])
        return {'verification_required':True}

    @app.post('/api/auth/confirm')
    def confirm(body:Confirmation,request:Request):
        throttle(request,body.email)
        provider('confirm_sign_up',ClientId=client_id(),Username=body.email.lower().strip(),ConfirmationCode=body.code)
        return {'confirmed':True}

    @app.post('/api/auth/resend')
    def resend(body:Identity,request:Request):
        throttle(request,body.email)
        provider('resend_confirmation_code',ClientId=client_id(),Username=body.email.lower().strip())
        return {'sent':True}

    @app.post('/api/auth/login')
    def login(body:Login,request:Request,response:Response):
        throttle(request,body.email)
        result=provider('initiate_auth',ClientId=client_id(),AuthFlow='USER_PASSWORD_AUTH',AuthParameters={'USERNAME':body.email.lower().strip(),'PASSWORD':body.password})
        auth=result.get('AuthenticationResult')
        if not auth: raise HTTPException(403,'This account requires an additional sign-in challenge. Contact support.')
        verified=provider('get_user',AccessToken=auth['AccessToken'])
        attrs={a['Name']:a['Value'] for a in verified['UserAttributes']}
        if attrs.get('email_verified')!='true' or attrs.get('custom:role')!=body.role:
            raise HTTPException(403,'Use the sign-in page for your verified account role.')
        sub=attrs['sub'];store=get_store()
        user=store.get('user#'+sub)
        if not user:
            try: user=store.put('user#'+sub,{'id':sub,'name':attrs.get('name','Participant'),'role':body.role,'projects':[],'epoch':uuid.uuid4().hex})
            except Conflict: user=store.get('user#'+sub)
        if user['role']!=body.role: raise HTTPException(403,'Account role mismatch.')
        lookup=store.get(email_key(body.email)) or {}
        store.put(email_key(body.email),{**lookup,'user_id':sub})
        token=secrets.token_urlsafe(32);key=hashlib.sha256(token.encode()).hexdigest()
        store.put('session#'+key,{'key':key,'type':'account','user_id':sub,'workspace':sub,'role':user['role'],'name':user['name'],'auth_epoch':user['epoch'],'expires':time.time()+min(auth.get('ExpiresIn',3600),3600),'projects':[]})
        response.set_cookie('proofpact_session',token,httponly=True,samesite='lax',secure=os.getenv('COOKIE_SECURE','false')=='true',max_age=3600)
        return {'role':user['role'],'name':user['name']}

    @app.post('/api/auth/logout')
    def logout(response:Response,s=Depends(session)):
        s['expires']=0;get_store().put('session#'+s['key'],s)
        response.delete_cookie('proofpact_session',secure=os.getenv('COOKIE_SECURE','false')=='true',httponly=True,samesite='lax')
        return {'signed_out':True}

    @app.post('/api/auth/forgot')
    def forgot(body:Identity,request:Request):
        throttle(request,body.email)
        try: provider('forgot_password',ClientId=client_id(),Username=body.email.lower().strip())
        except HTTPException as exc:
            if exc.status_code!=400: raise
        return {'message':'If this account can be recovered, a code will arrive by email.'}

    @app.post('/api/auth/reset')
    def reset(body:Reset,request:Request):
        throttle(request,body.email)
        provider('confirm_forgot_password',ClientId=client_id(),Username=body.email.lower().strip(),ConfirmationCode=body.code,Password=body.password)
        lookup=get_store().get(email_key(body.email))
        if lookup:
            user=get_store().get('user#'+lookup['user_id']);user['epoch']=uuid.uuid4().hex;get_store().put('user#'+user['id'],user)
        return {'reset':True}

    @app.post('/api/projects/{pid}/invite')
    def invite(pid:str,s=Depends(session)):
        p=project(pid,s)
        if s.get('type')!='account': raise HTTPException(403,'Sign in to invite another person.')
        other='builder' if s['role']=='client' else 'client'
        if p.get('members',{}).get(other): raise HTTPException(409,'Both participants have already joined.')
        consume(s,'invitations',10)
        token=secrets.token_urlsafe(32)
        get_store().put('invite#'+hashlib.sha256(token.encode()).hexdigest(),{'project_id':pid,'role':other,'expires':time.time()+86400*7,'claimed_by':None})
        return {'token':token,'role':other,'expires_in_days':7}

    @app.post('/api/invitations/accept')
    def accept(body:Invitation,s=Depends(session)):
        if s.get('type')!='account': raise HTTPException(403,'Sign in before joining a pact.')
        store=get_store();key='invite#'+hashlib.sha256(body.token.encode()).hexdigest();invite=store.get(key)
        if not invite or invite['expires']<time.time() or invite['role']!=s['role'] or invite.get('claimed_by') not in (None,s['user_id']): raise HTTPException(404,'Invitation is invalid, expired, or intended for the other role.')
        p=store.get('project#'+invite['project_id'])
        if not p or p.get('identity_mode')!='account': raise HTTPException(404,'Pact not found.')
        if s['user_id'] in p['members'].values() and p['members'].get(s['role'])!=s['user_id']: raise HTTPException(403,'A pact needs two different people.')
        if p['members'].get(s['role']) not in (None,s['user_id']): raise HTTPException(409,'This place has already been filled.')
        if not invite.get('claimed_by'):
            invite['claimed_by']=s['user_id'];store.put(key,invite)
        if not p['members'].get(s['role']):
            if p['state']!='BRIEFING': raise HTTPException(409,'This pact can no longer change participants.')
            p['members'][s['role']]=s['user_id'];p[s['role']]=s['name']
            event(p,s['role'],'Participant joined','A verified account joined this pact.');store.put('project#'+p['id'],p)
        add_project(store,s['user_id'],p['id'])
        return {'project_id':p['id']}
