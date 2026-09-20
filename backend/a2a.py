"""A2A 1.0 JSON-RPC adapter. Delegation never grants human approval authority."""
import copy
import hashlib
import json
import os
import secrets
import time
import uuid
from typing import Literal

from fastapi import Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from .domain import now as domain_now

def now(): return domain_now().replace("+00:00", "Z")
from .store import Conflict

ACTIONS = {
    'get_pact': 'Read the agreed scope and latest delivery result',
    'negotiate': 'Request a proposal from the private advocates; humans must approve',
    'check_change': 'Classify a new client request against the locked scope',
    'submit_delivery': 'Submit a builder delivery for the locked agreement',
    'verify_delivery': 'Run delivery checks; manual criteria still need human review',
}
ROLE_ACTIONS = {
    'client': {'get_pact', 'negotiate', 'check_change', 'verify_delivery'},
    'builder': {'get_pact', 'negotiate', 'submit_delivery', 'verify_delivery'},
}

class Command(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    action: Literal['get_pact', 'negotiate', 'check_change', 'submit_delivery', 'verify_delivery']
    expected_hash: str | None = Field(default=None, max_length=64)
    mode: Literal['demo', 'bedrock', 'modal'] = 'demo'
    text: str = Field(default='', max_length=2000)
    url: str = Field(default='', max_length=2000)
    notes: str = Field(default='', max_length=2000)

class Grant(BaseModel):
    model_config = ConfigDict(extra='forbid')
    allow_work: bool = False

class RPCError(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def card():
    origin = os.getenv('PUBLIC_ORIGIN', 'http://127.0.0.1:3000').rstrip('/')
    return {
        'name': 'ProofPact', 'version': '0.2.0',
        'description': 'Scope negotiation and delivery verification with human approval. Verified account or explicitly synthetic demo access; no live payment authority.',
        'supportedInterfaces': [{'url': origin + '/api/a2a', 'protocolBinding': 'JSONRPC', 'protocolVersion': '1.0'}],
        'capabilities': {'streaming': False, 'pushNotifications': False, 'extendedAgentCard': False},
        'securitySchemes': {'pactKey': {'httpAuthSecurityScheme': {'scheme': 'Bearer', 'description': 'One-hour pact and role scoped key, issued in the workspace Agents tab.'}}},
        'securityRequirements': [{'schemes': {'pactKey': {'list': []}}}],
        'defaultInputModes': ['application/json'], 'defaultOutputModes': ['application/json'],
        'documentationUrl': 'https://github.com/himanshu748/proofpact/blob/main/docs/a2a.md',
        'skills': [{'id': key, 'name': key.replace('_', ' ').title(), 'description': desc,
                    'tags': ['scope', 'delivery', 'human-approval'],
                    'examples': [json.dumps({'action': key})]} for key, desc in ACTIONS.items()],
    }


def snapshot(p):
    """Small allowlisted artifact, not the private briefs or payment record."""
    result = {k: copy.deepcopy(p.get(k)) for k in ('id', 'name', 'state', 'current', 'hash', 'approvals', 'delivery')}
    pending = p.get('pending_amendment')
    result['pending_amendment'] = ({k: copy.deepcopy(pending[k]) for k in ('agreement', 'hash', 'base_hash', 'approvals')} if pending else None)
    run = (p.get('runs') or [None])[-1]
    result['verification'] = ({k: copy.deepcopy(v) for k, v in run.items() if k in ('id', 'hash', 'version', 'at', 'results')} if run else None)
    if result['verification']:
        for row in result['verification'].get('results', []):
            row.pop('evidence', None)
    if p.get('changes'):
        result['latest_change'] = copy.deepcopy(p['changes'][-1])
    result['human_authority'] = 'Agents cannot approve agreements, review manual criteria, publish receipts, or move money.'
    return result


def install(app, get_store, session, project, consume, execute):
    def access_key(pid, role): return f'a2a-access#{pid}#{role}'

    @app.get('/.well-known/agent-card.json')
    @app.get('/api/a2a/agent-card')
    def agent_card(): return card()

    @app.post('/api/projects/{pid}/agent-access')
    def issue(pid: str, body: Grant, s=Depends(session)):
        project(pid, s)
        consume(s, 'agent-keys', 20)
        key = access_key(pid, s['role'])
        old = get_store().get(key) or {}
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        grant = {**old, 'id': str(uuid.uuid4()), 'project_id': pid, 'workspace': s['workspace'],
                 'role': s['role'], 'expires': min(s['expires'], time.time() + 3600),
                 'scopes': sorted(ROLE_ACTIONS[s['role']] if body.allow_work else {'get_pact'}),
                 'revoked': False, **{k:s[k] for k in ('type','user_id','auth_epoch') if k in s}}
        # Rotation first invalidates the old key. Store only a digest lookup, never the token.
        get_store().put(key, grant)
        get_store().put('a2a-key#' + token_hash, {'access_key': key, 'id': grant['id']})
        return {'token': token, **{k: grant[k] for k in ('id', 'role', 'expires', 'scopes')}, 'agent_card': card()}

    @app.get('/api/projects/{pid}/agent-access')
    def access_status(pid: str, s=Depends(session)):
        project(pid, s)
        grant = get_store().get(access_key(pid, s['role']))
        if not grant: return {'active': False}
        return {'active': not grant['revoked'] and grant['expires'] > time.time(),
                **{k: grant[k] for k in ('id', 'role', 'expires', 'scopes')}}

    @app.delete('/api/projects/{pid}/agent-access')
    def revoke(pid: str, s=Depends(session)):
        project(pid, s)
        key = access_key(pid, s['role'])
        grant = get_store().get(key)
        if grant:
            grant['revoked'] = True
            get_store().put(key, grant)
        return {'active': False}

    def authenticate(request):
        scheme, _, token = request.headers.get('authorization', '').partition(' ')
        lookup = get_store().get('a2a-key#' + hashlib.sha256(token.encode()).hexdigest()) if scheme.lower() == 'bearer' and token else None
        grant = get_store().get(lookup['access_key']) if lookup else None
        if not grant or grant['id'] != lookup['id'] or grant['revoked'] or grant['expires'] <= time.time():
            raise HTTPException(401, 'A valid pact agent key is required.', headers={'WWW-Authenticate': 'Bearer'})
        project(grant['project_id'], grant)
        return grant

    def task_record(task_id, grant):
        record = get_store().get('a2a-task#' + task_id)
        if not record or record['access_id'] != grant['id']:
            raise RPCError(-32001, 'Task not found')
        return record

    def public_task(record, history_length=None, artifacts=True):
        task = copy.deepcopy(record['task'])
        if history_length == 0: task.pop('history', None)
        elif history_length is not None: task['history'] = task.get('history', [])[-history_length:]
        if not artifacts: task.pop('artifacts', None)
        return task

    def bounded_int(value, default, low=0, high=100):
        value = default if value is None else value
        if type(value) is not int or not low <= value <= high: raise RPCError(-32602, 'Invalid integer parameter')
        return value

    def run(params, grant):
        message = params.get('message')
        if not isinstance(message, dict) or message.get('role') != 'ROLE_USER': raise RPCError(-32602, 'A ROLE_USER message is required')
        mid = message.get('messageId')
        if not isinstance(mid, str) or not 1 <= len(mid) <= 128: raise RPCError(-32602, 'A messageId of 1–128 characters is required')
        if message.get('contextId') not in (None, grant['project_id']): raise RPCError(-32602, 'Context does not match this pact')
        if message.get('taskId'):
            task_record(message['taskId'], grant)
            raise RPCError(-32004, 'Tasks are single-operation; send a new messageId for a new operation')
        config = params.get('configuration', {})
        if not isinstance(config, dict): raise RPCError(-32602, 'Invalid configuration')
        if config.get('taskPushNotificationConfig'): raise RPCError(-32003, 'Push notifications are not supported')
        if config.get('returnImmediately'): raise RPCError(-32004, 'Only blocking execution is supported')
        modes = config.get('acceptedOutputModes', ['application/json'])
        if not isinstance(modes, list) or (modes and 'application/json' not in modes): raise RPCError(-32005, 'application/json output is required')
        history = bounded_int(config.get('historyLength'), 1)
        parts = message.get('parts')
        if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict) or set(parts[0]) - {'data', 'mediaType'} or not isinstance(parts[0].get('data'), dict):
            raise RPCError(-32602, 'Send one structured data part containing a ProofPact command')
        if parts[0].get('mediaType', 'application/json') != 'application/json': raise RPCError(-32005, 'Only application/json data parts are supported')
        try: command = Command.model_validate(parts[0]['data'])
        except ValidationError: raise RPCError(-32602, 'Invalid ProofPact command; see the Agent Card documentation')
        if command.action not in grant['scopes']: raise RPCError(-32004, 'This key does not allow that action')
        tid = str(uuid.uuid5(uuid.NAMESPACE_URL, grant['id'] + ':' + mid))
        key = 'a2a-task#' + tid
        fingerprint = hashlib.sha256(json.dumps(message, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        existing = get_store().get(key)
        if existing:
            if existing['fingerprint'] != fingerprint: raise RPCError(-32602, 'messageId was already used for a different message')
            if existing['task']['status']['state'] == 'TASK_STATE_WORKING': raise RPCError(-32004, 'Task is still working or needs reconciliation; use GetTask. The operation will not be repeated.')
            return {'task': public_task(existing, history)}
        p = project(grant['project_id'], grant)
        if command.action != 'get_pact' and (not command.expected_hash or command.expected_hash != (p.get('hash') or 'unversioned')):
            raise RPCError(-32602, 'Refresh the pact and supply its current expected_hash')
        consume(grant, 'a2a-tasks', 50)
        task = {'id': tid, 'contextId': grant['project_id'], 'status': {'state': 'TASK_STATE_WORKING', 'timestamp': now()},
                'history': [message], 'metadata': {'action': command.action, 'participantRole': grant['role']}}
        try:
            record = get_store().put(key, {'access_id': grant['id'], 'fingerprint': fingerprint, 'task': task})
        except Conflict: raise RPCError(-32004, 'This message is already being processed; use GetTask')
        # Index before execution; if interrupted, the reserved task cannot execute twice.
        index_key = 'a2a-index#' + grant['id']
        try:
            for attempt in range(5):
                index = get_store().get(index_key) or {'ids': []}
                if len(index['ids']) >= 100: raise RPCError(-32004, 'This key has reached its task limit; rotate it in the workspace')
                index['ids'].append(tid)
                try:
                    get_store().put(index_key, index)
                    break
                except Conflict:
                    if attempt == 4: raise
            active = get_store().get(access_key(grant['project_id'], grant['role']))
            if not active or active['id'] != grant['id'] or active['revoked'] or active['expires'] <= time.time():
                raise HTTPException(401, 'Agent access expired or was revoked before execution.')
            result = execute(command, grant)
            task['status'] = {'state': 'TASK_STATE_COMPLETED', 'timestamp': now()}
            task['artifacts'] = [{'artifactId': str(uuid.uuid4()), 'name': 'Pact result',
                                  'parts': [{'data': snapshot(result), 'mediaType': 'application/json'}]}]
        except Exception as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else 'Operation could not complete. Refresh the pact before sending a new request.'
            task['status'] = {'state': 'TASK_STATE_FAILED', 'timestamp': now(), 'message': {
                'messageId': str(uuid.uuid4()), 'contextId': grant['project_id'], 'taskId': tid,
                'role': 'ROLE_AGENT', 'parts': [{'text': str(detail)}]}}
        record['task'] = task
        record = get_store().put(key, record)
        return {'task': public_task(record, history)}

    def dispatch(method, params, grant):
        if params.get('tenant'): raise RPCError(-32602, 'Tenants are not supported by this interface')
        if method == 'SendMessage': return run(params, grant)
        if method in ('GetTask', 'CancelTask'):
            tid = params.get('id')
            if not isinstance(tid, str): raise RPCError(-32602, 'A task id is required')
            record = task_record(tid, grant)
            if method == 'CancelTask': raise RPCError(-32002, 'This blocking operation cannot be safely canceled; no cancellation was performed')
            return public_task(record, bounded_int(params.get('historyLength'), 1))
        if method == 'ListTasks':
            size = bounded_int(params.get('pageSize'), 50, 1)
            history = bounded_int(params.get('historyLength'), 0)
            index = get_store().get('a2a-index#' + grant['id']) or {'ids': []}
            records = [task_record(tid, grant) for tid in index['ids']]
            records.sort(key=lambda r: (r['task']['status']['timestamp'], r['task']['id']), reverse=True)
            if params.get('contextId') not in (None, grant['project_id']): records = []
            status = params.get('status')
            if status:
                if status not in ('TASK_STATE_SUBMITTED', 'TASK_STATE_WORKING', 'TASK_STATE_COMPLETED', 'TASK_STATE_FAILED', 'TASK_STATE_CANCELED', 'TASK_STATE_REJECTED', 'TASK_STATE_INPUT_REQUIRED', 'TASK_STATE_AUTH_REQUIRED', 'TASK_STATE_UNSPECIFIED'): raise RPCError(-32602, 'Invalid status filter')
                records = [r for r in records if r['task']['status']['state'] == status]
            after = params.get('statusTimestampAfter')
            if after:
                from datetime import datetime
                try: cutoff = datetime.fromisoformat(after.replace('Z', '+00:00'))
                except (ValueError, AttributeError): raise RPCError(-32602, 'Invalid timestamp')
                if cutoff.tzinfo is None: raise RPCError(-32602, 'Timestamp needs a timezone')
                records = [r for r in records if datetime.fromisoformat(r['task']['status']['timestamp'].replace('Z', '+00:00')) >= cutoff]
            total = len(records)
            cursor = params.get('pageToken', '')
            if cursor:
                positions = [i for i, r in enumerate(records) if r['task']['id'] == cursor]
                if not positions: raise RPCError(-32602, 'Invalid page token')
                records = records[positions[0] + 1:]
            page = records[:size]
            return {'tasks': [public_task(r, history, params.get('includeArtifacts') is True) for r in page],
                    'nextPageToken': page[-1]['task']['id'] if len(records) > size else '', 'pageSize': size, 'totalSize': total}
        if 'PushNotification' in method: raise RPCError(-32003, 'Push notifications are not supported')
        if method in ('SendStreamingMessage', 'SubscribeToTask', 'GetExtendedAgentCard'): raise RPCError(-32004, 'Operation not supported')
        raise RPCError(-32601, 'Method not found')

    @app.post('/api/a2a')
    async def rpc(request: Request):
        grant = authenticate(request)
        request_id = None
        try:
            try: body = await request.json()
            except (ValueError, UnicodeDecodeError): raise RPCError(-32700, 'Invalid JSON payload')
            if not isinstance(body, dict) or body.get('jsonrpc') != '2.0' or not isinstance(body.get('method'), str) or type(body.get('id')) not in (str, int):
                raise RPCError(-32600, 'A JSON-RPC 2.0 request with an id is required; batches and notifications are unsupported')
            request_id = body['id']
            version = request.headers.get('a2a-version', request.query_params.get('A2A-Version', '0.3'))
            if version.split('.')[:2] != ['1', '0']: raise RPCError(-32009, 'Protocol version not supported; send A2A-Version: 1.0')
            params = body.get('params', {})
            if not isinstance(params, dict): raise RPCError(-32602, 'Invalid parameters')
            result = await run_in_threadpool(dispatch, body['method'], params, grant)
            response = {'jsonrpc': '2.0', 'id': request_id, 'result': result}
        except RPCError as exc:
            response = {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': exc.code, 'message': exc.message}}
        except (HTTPException, Conflict):
            response = {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32004, 'message': 'Request unavailable or rate limited; refresh the pact before retrying'}}
        except Exception:
            response = {'jsonrpc': '2.0', 'id': request_id, 'error': {'code': -32603, 'message': 'Internal error'}}
        return JSONResponse(response, headers={'A2A-Version': '1.0', 'Cache-Control': 'no-store'})
