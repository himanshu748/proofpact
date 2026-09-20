# Participant accounts and observable acceptance

Client and freelancer sign-in pages use Cognito email/password accounts. Email verification is required before access. Each account has one immutable role. Email ownership verification is not legal identity verification.

Deploy `infra/auth.yaml`, then supply its public `ClientId` as `CognitoClientId` when updating `infra/application.yaml`. Local development uses `COGNITO_CLIENT_ID`. Passwords go to Cognito and are never stored in application records. Opaque HttpOnly sessions expire within one hour. Password recovery through this application invalidates existing app sessions and agent grants.

A participant creates a pact with deliverables, observable acceptance criteria and a revision window of 1–30 days. They share a single-use, seven-day invitation with the opposite role. Treat the invitation as a secret: the first matching account with the link can claim it. Both participants must join before negotiation. Each sees only their own private brief; shared proposals are visible to both.

The agreement hash covers criteria, revision policy and the named client delivery approver. Both people must approve the same version. New requests remain pending amendments until both approve. Revision requests reference existing criteria and close after the agreed number of days from first submission. Resubmission does not restart that clock. An accepted amendment starts a new delivery cycle. Expiry never accepts work or releases payment. Older agreements without a revision policy need an amendment.

The explicitly labelled demo keeps synthetic role switching. Real accounts cannot switch roles or read demo workspaces. A2A keys inherit account membership and cannot approve agreements or payments.

Operational limits: Cognito default email delivery has provider quotas; configure production email delivery before broader onboarding. MFA challenge UI is not implemented. Email delivery and recovery require end-to-end inbox testing. Payments remain disabled while Razorpay Route access is pending.

Cognito attribute behavior: https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-attributes.html

## Validation recorded

Account and agreement coverage passes with 55 backend tests. Real Cognito login was exercised locally and against the AWS deployment using two temporary, administrator-confirmed synthetic accounts with email delivery suppressed. Hosted invitation acceptance, unauthorized access rejection, private-brief separation, fixed roles and logout passed. Both temporary identities were deleted afterward. This does not test receipt of signup or password-recovery emails. Browser checks covered both sign-in pages, mobile layout, the separate demo and legacy agreement terms.
