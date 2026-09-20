"""Razorpay Route sandbox integration; live keys are deliberately rejected.

One funded milestone per pact. Provider reads establish funding, never browser
callbacks. Ambiguous writes stay blocked for operator reconciliation.
"""
import hashlib
import hmac
import json
import os
import re

import httpx
from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field
from .domain import digest, event, now, public_project


def settings():
    key = os.getenv('RAZORPAY_KEY_ID', '')
    account = os.getenv('RAZORPAY_LINKED_ACCOUNT_ID', '')
    enabled = (os.getenv('PAYMENTS_MODE') == 'razorpay_test' and
               key.startswith('rzp_test_') and bool(os.getenv('RAZORPAY_KEY_SECRET')) and
               bool(re.fullmatch(r'acc_[A-Za-z0-9]+', account)))
    return {'configured': enabled, 'mode': 'test', 'live_enabled': False}


class Razorpay:
    def __init__(self):
        if not settings()['configured']:
            raise HTTPException(503, 'Razorpay Route test credentials and a test linked account must be configured. Live payments are disabled.')
        self.key = os.environ['RAZORPAY_KEY_ID']
        self.account = os.environ['RAZORPAY_LINKED_ACCOUNT_ID']

    def request(self, method, path, data=None):
        try:
            with httpx.Client(base_url='https://api.razorpay.com/v1/',
                              auth=(self.key, os.environ['RAZORPAY_KEY_SECRET']), timeout=20) as client:
                result = client.request(method, path, json=data)
                result.raise_for_status()
                return result.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, 'Razorpay could not confirm this operation. Refresh payment status; do not start another payment.')

    def create(self, p):
        return self.request('POST', 'orders', {
            'amount': p['current']['price_minor'], 'currency': 'INR', 'partial_payment': False,
            'receipt': p['id'], 'notes': {'project_id': p['id'], 'agreement_hash': p['hash']},
            'transfers': [{'account': self.account, 'amount': p['current']['price_minor'],
                           'currency': 'INR', 'on_hold': True,
                           'notes': {'agreement_hash': p['hash']}}],
        })

    def order(self, order_id):
        return self.request('GET', f'orders/{order_id}?expand[]=transfers')

    def release(self, transfer_id):
        return self.request('PATCH', f'transfers/{transfer_id}', {'on_hold': False})


def validate_order(order, payment):
    if (order.get('id') != payment['order_id'] or order.get('amount') != payment['amount_minor'] or
            order.get('currency') != 'INR' or order.get('notes', {}).get('agreement_hash') != payment['agreement_hash']):
        raise HTTPException(409, 'Provider order does not match the locked agreement. Operator review required.')


def observe(order, payment):
    validate_order(order, payment)
    if order.get('status') != 'paid' or order.get('amount_paid') != payment['amount_minor'] or order.get('amount_due') != 0:
        return 'AWAITING_PAYMENT'
    transfers = order.get('transfers', {}).get('items', [])
    if not transfers:
        return 'TRANSFER_PENDING'
    if len(transfers) != 1:
        raise HTTPException(409, 'Unexpected transfer count. Operator review required.')
    t = transfers[0]
    if (t.get('recipient') != payment['recipient'] or t.get('amount') != payment['amount_minor'] or
            t.get('currency') != 'INR' or t.get('source') != payment['order_id'] or
            not re.fullmatch(r'trf_[A-Za-z0-9]+', t.get('id', ''))):
        raise HTTPException(409, 'Transfer does not match this milestone. Operator review required.')
    if payment.get('transfer_id') and payment['transfer_id'] != t['id']:
        raise HTTPException(409, 'Transfer identity changed. Operator review required.')
    payment['transfer_id'] = t['id']
    if t.get('amount_reversed', 0) or t.get('status') in ('failed', 'reversed', 'partially_reversed'):
        return 'REVIEW_REQUIRED'
    if t.get('status') != 'processed':
        return 'TRANSFER_PENDING'
    if t.get('on_hold') is True and not t.get('on_hold_until') and t.get('settlement_status') == 'on_hold':
        return 'FUNDED'
    if not payment.get('release_approval'):
        return 'REVIEW_REQUIRED'
    if t.get('settlement_status') == 'settled':
        return 'SETTLED'
    if t.get('on_hold') is False:
        return 'RELEASE_PENDING'
    return 'REVIEW_REQUIRED'


class Reviewed(BaseModel):
    content_hash: str
    reviewed: bool


class CheckoutResult(BaseModel):
    razorpay_order_id: str = Field(pattern=r'^order_[A-Za-z0-9]+$')
    razorpay_payment_id: str = Field(pattern=r'^pay_[A-Za-z0-9]+$')
    razorpay_signature: str = Field(pattern=r'^[0-9a-f]{64}$')


class Dispute(BaseModel):
    reason: str = Field(min_length=10, max_length=2000)


def install(app, get_store, session, project, role, consume):
    def write(p):
        return get_store().put('project#' + p['id'], p)

    def checked(p, body):
        if not body.reviewed or body.content_hash != p.get('hash') or digest(p['current']) != p['hash']:
            raise HTTPException(409, 'Review the exact current agreement before continuing.')
        if set(p['approvals']) != {'client', 'builder'} or any(a['hash'] != p['hash'] for a in p['approvals'].values()):
            raise HTTPException(409, 'Both participants must approve this agreement.')
        if p.get('pending_amendment'):
            raise HTTPException(409, 'Resolve the pending amendment before funding or releasing this milestone.')

    def reconcile(p):
        payment = p.get('payment')
        if not payment or not payment.get('order_id'):
            raise HTTPException(409, 'No confirmed order is available. An uncertain creation requires operator reconciliation.')
        if payment.get('operation'):
            raise HTTPException(409, 'A provider operation is unresolved. Operator reconciliation is required before further actions.')
        observed = observe(Razorpay().order(payment['order_id']), payment)
        payment['provider_status'] = observed
        payment['status'] = 'DISPUTED' if payment.get('dispute') and observed == 'FUNDED' else observed
        payment['checked_at'] = now()
        return write(p)

    @app.get('/api/payments/config')
    def config():
        return settings()

    @app.post('/api/projects/{pid}/payment/order')
    def create_order(pid: str, body: Reviewed, s=Depends(session)):
        role(s, 'client')
        p = project(pid, s)
        provider = Razorpay()
        checked(p, body)
        if p['state'] != 'AGREEMENT_LOCKED' or p.get('delivery'):
            raise HTTPException(409, 'Fund the milestone after approval and before delivery.')
        if p.get('payment'):
            payment = p['payment']
            if payment.get('order_id') and payment['status'] == 'AWAITING_PAYMENT':
                return {'project': public_project(p), 'checkout': {'key': provider.key, 'order_id': payment['order_id'], 'amount': payment['amount_minor'], 'currency': 'INR'}}
            raise HTTPException(409, 'This pact already has a payment record. Refresh its status instead.')
        consume(s, 'payment_orders', 5)
        p['payment'] = {'mode': 'test', 'agreement_hash': p['hash'], 'amount_minor': p['current']['price_minor'],
                        'currency': 'INR', 'recipient': provider.account, 'status': 'CREATING',
                        'operation': 'create', 'created_at': now()}
        p = write(p)  # CAS reservation prevents concurrent duplicate orders.
        order = provider.create(p)  # Ambiguous failure keeps the reservation; no blind POST retry.
        if not re.fullmatch(r'order_[A-Za-z0-9]+', order.get('id', '')):
            raise HTTPException(502, 'Razorpay returned an invalid order. Operator reconciliation required.')
        p['payment']['order_id'] = order['id']
        validate_order(order, p['payment'])
        p['payment'].update(status='AWAITING_PAYMENT', operation=None)
        event(p, 'client', 'Test milestone order created', 'No real money. Funding must be confirmed by Razorpay before work begins.')
        p = write(p)
        get_store().put('payment-order#' + order['id'], {'project_id': p['id']})
        return {'project': public_project(p), 'checkout': {'key': provider.key, 'order_id': order['id'], 'amount': p['payment']['amount_minor'], 'currency': 'INR'}}

    @app.post('/api/projects/{pid}/payment/confirm')
    def confirm(pid: str, body: CheckoutResult, s=Depends(session)):
        role(s, 'client'); p = project(pid, s); payment = p.get('payment') or {}
        Razorpay()
        if payment.get('order_id') != body.razorpay_order_id:
            raise HTTPException(400, 'Checkout belongs to a different order.')
        signature = hmac.new(os.environ['RAZORPAY_KEY_SECRET'].encode(),
                             (payment['order_id'] + '|' + body.razorpay_payment_id).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, body.razorpay_signature):
            raise HTTPException(400, 'Checkout signature is invalid.')
        return public_project(reconcile(p))

    @app.post('/api/projects/{pid}/payment/refresh')
    def refresh(pid: str, s=Depends(session)):
        return public_project(reconcile(project(pid, s)))

    @app.post('/api/projects/{pid}/payment/dispute')
    def dispute(pid: str, body: Dispute, s=Depends(session)):
        p = project(pid, s); payment = p.get('payment') or {}
        if payment.get('status') != 'FUNDED' or payment.get('operation'):
            raise HTTPException(409, 'Only a funded, held milestone can enter dispute review.')
        payment.update(status='DISPUTED', dispute={'by': s['role'], 'reason': body.reason.strip(), 'at': now()})
        event(p, s['role'], 'Milestone disputed', 'Release is blocked. An operator must review the evidence and arrange a resolution with both parties.')
        return public_project(write(p))

    @app.post('/api/projects/{pid}/payment/release')
    def release(pid: str, body: Reviewed, s=Depends(session)):
        role(s, 'client'); p = project(pid, s); checked(p, body)
        payment = p.get('payment') or {}
        if payment.get('status') != 'FUNDED' or payment.get('dispute') or payment.get('operation') or payment.get('agreement_hash') != p['hash']:
            raise HTTPException(409, 'The matching milestone must be funded, held and undisputed.')
        run = p['runs'][-1] if p['runs'] else {}
        delivery = p.get('delivery') or {}
        if (p['state'] != 'VERIFIED' or run.get('agreement_hash') != p['hash'] or run.get('url') != delivery.get('url') or
                not run.get('at') or run['at'] < delivery.get('at', '') or not run.get('results') or
                any(r['status'] != 'passed' for r in run['results'])):
            raise HTTPException(409, 'Verify the current delivery, including human review, before approving release.')
        provider = Razorpay()
        if observe(provider.order(payment['order_id']), payment) != 'FUNDED':
            raise HTTPException(409, 'Razorpay has not confirmed that this full milestone is on hold.')
        payment.update(status='RELEASING', operation='release', release_approval={'role': 'client', 'hash': p['hash'], 'run_id': run['id'], 'at': now()})
        p = write(p)  # Blocks disputes and amendments while the external write runs.
        provider.release(payment['transfer_id'])
        p['payment']['operation'] = None
        p['payment']['status'] = 'RELEASE_PENDING'
        event(p, 'client', 'Test release requested', 'Razorpay settlement is pending. This does not yet mean the builder has been paid.')
        p = write(p)
        return public_project(reconcile(p))

    @app.post('/api/payments/webhook')
    async def webhook(request: Request):
        secret = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')
        if not secret or not settings()['configured']:
            raise HTTPException(503, 'Test webhook is not configured.')
        raw = await request.body()
        expected = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, request.headers.get('x-razorpay-signature', '')):
            raise HTTPException(400, 'Webhook signature is invalid.')
        try:
            message = json.loads(raw)
            order_id = message.get('payload', {}).get('payment', {}).get('entity', {}).get('order_id')
            if not order_id:
                order_id = message.get('payload', {}).get('order', {}).get('entity', {}).get('id')
        except (ValueError, AttributeError):
            raise HTTPException(400, 'Invalid webhook payload.')
        if not isinstance(order_id, str) or not re.fullmatch(r'order_[A-Za-z0-9]+', order_id):
            return {'received': True, 'reconciled': False}
        index = get_store().get('payment-order#' + order_id)
        if not index:
            return {'received': True, 'reconciled': False}
        p = get_store().get('project#' + index['project_id'])
        # Duplicate and out-of-order events only trigger a current provider read.
        # No webhook-supplied status, amount, recipient or release instruction is trusted.
        from starlette.concurrency import run_in_threadpool
        await run_in_threadpool(reconcile, p)
        return {'received': True, 'reconciled': True}
