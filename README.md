# ProofPact

A hackathon demo for agreeing on software scope, approving an exact version, and checking delivery against its acceptance criteria.

[Live AWS demo](https://kys3pqjxvy4fbljl7xqp2zzssu0pxmxo.lambda-url.us-east-1.on.aws/) · [Verified synthetic receipt](https://kys3pqjxvy4fbljl7xqp2zzssu0pxmxo.lambda-url.us-east-1.on.aws/proof/J8HU-vXRBb5O4AuFidfeHEQ_hFwtFsEc)

September 19 hosted validation: 26 backend tests, production frontend build, format check, real hosted Modal proposal, and hosted broken/fixed CSV flow passed. Ten screenshot objects were confirmed in private S3 with all public-access blocks enabled.

Latest source update: pending amendments stay separate from the active agreement until both participants approve the exact proposed version. Existing delivery and evidence remain valid while a change is pending. This fix passes 27 backend tests and TypeScript checks locally; it is not yet included in the hosted demo.

September 20 payment integration: 39 backend tests, TypeScript, production build and formatting pass. The local Payments screen was browser-checked with disconnected credentials. Provider API behavior is tested with mocked responses; a real Razorpay Route sandbox round trip is still pending linked-account setup. The update is deployed to AWS; hosted checks confirm payments remain disabled without complete provider configuration and pending amendments preserve the active agreement hash. Recovered test credentials authenticate with Razorpay, but Route readiness is not yet verified.

## Run locally

Install Node dependencies with `npm ci`. Create a Python virtual environment, install `backend/requirements.txt`, and run `python -m playwright install chromium`.

Start the API with `.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000`. In another terminal, run `npm run dev`, then open `http://127.0.0.1:3000`.

The default SQLite database and screenshots live under `backend/data/`, excluded from source uploads. Real Modal inference requires an authenticated Modal SDK and the deployed `proofpact-inference` app from `infra/modal_inference.py`.

## Demo flow

1. Open the workspace. The Acme agreement starts with explicitly labeled sample proposals.
2. Review and approve as the synthetic client. Switch the demo role and approve as the synthetic builder.
3. Submit the Broken CSV target and run verification. Its export contains 10 of 27 records.
4. Submit the Fixed CSV target and run verification again. Its export contains all 27 records.
5. Switch to the client, inspect the mobile screenshot, and record the visual review.
6. Open Proof of Done and create a share link. The public receipt omits raw screenshots, CSV contents, and private briefs.

Real negotiation is available separately from the sample proposal. Each advocate receives the shared requirements and only its own private brief. Outputs must satisfy a strict schema and retain every required scope item. A deterministic validator checks both parties' limits. An agent proposal never creates human approval.

## Verification

```sh
.venv/bin/python -m pytest backend/tests -q
npm run build
npm run format:check
.venv/bin/python -m scripts.check_negotiation modal
.venv/bin/python scripts/check_delivery.py http://127.0.0.1:8000
```

The model smoke test makes paid remote inference calls using synthetic data. The delivery test creates a new synthetic workspace, runs actual Chromium checks, verifies session protection for screenshots, and checks public receipt redaction. Its human-review step exercises the API; it does not replace a person's visual assessment.

## AWS deployment

`infra/bootstrap.yaml` defines private DynamoDB storage, a private S3 evidence bucket, ECR, CodeBuild, narrow runtime permissions, and seven-day logs. `scripts/prepare_aws_build.py` packages an explicit source allowlist, stores an existing Modal credential in Secrets Manager if absent, and starts CodeBuild. It never prints credential values.

`infra/application.yaml` runs the resulting immutable image on Lambda with Lambda Web Adapter. Deploy with the image digest and bootstrap outputs. After the function URL is created, update the `PublicOrigin` parameter to that exact origin before browser use. The public function exposes the synthetic demo; DynamoDB records and S3 evidence remain behind the application session checks.

Production build output, local records, credentials, and screenshots are excluded from the uploaded source archive. AWS screenshots use the private S3 bucket; role-checked API requests return the bytes. Evidence expires after 30 days.

## Current boundaries

- This is a synthetic demo with explicit role switching, not production multiuser authentication.
- Razorpay Route milestone funding is implemented for test keys only. Checkout, provider reconciliation, signed webhooks, dispute blocking and explicit release are covered by automated tests. No live money is supported. See [payment setup and boundaries](docs/payments.md).
- Advocates are backend-orchestrated private contexts. The A2A protocol is not implemented.
- Modal CPU inference is slow: the successful September 19 smoke negotiation took 106 seconds. It can decline or fail; sample mode is separately labeled.
- Bedrock remains an implemented option, but live calls on September 19 were blocked by the account's daily token quota.
- Automated checks support the supplied test contract. Custom requirements require human review; arbitrary sites are not claimed as automatically verified.
- Verification URLs are restricted to explicit synthetic fixtures or operator-allowlisted HTTPS hosts. Cross-origin browser requests and non-read requests are blocked.
- A receipt records checks at a point in time. It is not a legal contract or a guarantee of future behavior.

Implementation and documentation were developed with Codex assistance. Hackathon submission artifacts and production authentication remain separate work.
