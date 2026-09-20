# Razorpay Route milestone funding

This implementation is **test mode only**, with one milestone and one operator-configured test recipient per pact. It is not production escrow or a live marketplace. Synthetic roles are switchable; live keys are rejected in code.

## Setup

Enable Razorpay Route in your test account and create a test linked account. Configure these backend environment variables through your local shell or a deployment secret store (never through Git):

- `PAYMENTS_MODE=razorpay_test`
- `RAZORPAY_KEY_ID` (must start with `rzp_test_`)
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_LINKED_ACCOUNT_ID`
- `RAZORPAY_WEBHOOK_SECRET`

The app does not automatically load `.env` files. Export variables before starting the API. The public AWS deployment currently has no payment credentials configured.

Configure payment-captured/order-paid webhooks to `https://YOUR_ORIGIN/api/payments/webhook`. Set the same webhook secret on both sides. Raw-body HMAC validation precedes parsing; each notification prompts a fresh provider read. Repeated or out-of-order notifications cannot fabricate funding or trigger release. The Refresh payment status button also reconciles Route transfer and settlement state.

## Flow

1. Both participants approve the exact agreement hash.
2. Client explicitly reviews the funding terms and opens Razorpay test checkout. The server derives the amount and currency from the agreement, and the recipient from operator configuration. Order transfers use `on_hold=true`, no automatic release date, and no partial payments.
3. A signed checkout callback is verified, but only a provider read confirming the full paid order and processed, held transfer marks the milestone funded.
4. Builder submits; verification checks the current delivery. Human review remains mandatory wherever the criterion requires it.
5. Either participant can open a dispute while funds are held. This blocks release. Resolution/refund is an operator-assisted process; this version has no automated refund or dispute-resolution endpoint.
6. Client explicitly approves release after verification. The server checks the agreement, current run, transfer recipient, amount and hold again before requesting release. A successful release request means settlement pending, not money received. Refresh confirms settlement later.

A pact with a payment record cannot change its agreement. New scope must wait for resolution or use a separate pact. Unfunded pacts retain the original demo flow; funding is optional until production participant accounts are implemented.

## Failure handling

The server reserves provider writes with an optimistic version check before calling Razorpay. A timed-out creation or release remains blocked, preventing blind duplicate attempts. An operator must reconcile uncertain operations against the Razorpay dashboard and persisted agreement/order/transfer identifiers before clearing the operation. Do not delete a pending record to retry or infer payment from a browser success screen.

Provider mismatches, reversals and unexpected releases require review. There is no automatic payout based on AI output, a passing browser check, a webhook payload, or a deadline.

## Remaining before real money

Verified production users and per-project participant access, recipient onboarding, provider approval of the business and holding terms, durable reconciliation jobs, an operator dispute/refund console and policy, and live payment review. The sandbox recipient is not a substitute for identifying each builder. Test credentials do not establish Route availability.

Official references: [Route API checklist](https://razorpay.com/docs/payments/route/apis/), [settlement holds](https://razorpay.com/docs/api/payments/route/modify-settlement-hold/), [webhook validation](https://razorpay.com/docs/webhooks/validate-test/).
