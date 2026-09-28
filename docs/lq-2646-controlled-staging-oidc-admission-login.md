# LQ-2646 — Controlled staging OIDC admission login

## Status

Implemented as a repository slice. Staging execution remains a separate,
explicitly authorized operational step after review, merge, release and
promotion of the containing revision.

## Objective

LQ-2646 closes the gap identified by LQ-2645 between a working Google OIDC
redirect and the existing persistent identity-admission contract. It provides
an offline operator path which can provision one authorized admission and bind
it to one current pending OIDC login without exposing an admission handle or
login state to the browser.

The slice does not make public login an admission API. A person starts the
ordinary Google login flow and pauses at Google. An authorized operator then
runs the command against the system of record. The browser can continue only
after the server-side binding succeeds.

## Observable contract

The operator request contains exactly:

- the stable internal actor user ID;
- one stable onboarding decision ID;
- the stable target user ID; and
- the stable target workspace ID.

The request is accepted only from a private local file. It contains no login
state, admission ID, issuer, subject, role, permission, capability claim,
caller-supplied allow value, redirect URI or time value.

The existing authorized onboarding chain resolves authority from persistent
facts. A session principal identifies the actor but does not grant authority.
The active actor, target user, target workspace and workspace-scoped onboarding
management capability remain system-of-record decisions. Ordinary membership
and research permissions remain unrelated.

If onboarding is authorized, the existing retry-safe provisioning store
creates or resolves exactly one short-lived identity admission for the stable
decision. The new binding adapter then resolves pending browser state from the
same database transaction boundary rather than accepting it from the caller.

## Binding rules

Binding succeeds only when all of the following are true:

- the admission exists and is not consumed or expired;
- its target user and target workspace are active;
- exactly one current unbound OIDC login transaction is pending; and
- the conditional update still owns that pending transaction.

Zero eligible pending logins is a neutral rejection. More than one eligible
pending login is also a neutral rejection because the target browser cannot be
selected unambiguously. Neither outcome changes a login transaction.

An exact retry succeeds when the same admission is already attached to exactly
one current pending login. An impossible or corrupted multiple binding is
detail-free technical unavailability. Database, clock, decoding and atomicity
failures use the existing OIDC login-transaction unavailability boundary; this
slice introduces no new persistence exception.

The admission itself remains the callback's authority-bearing input. The
callback must still consume it atomically while binding the provider identity.
Expiration, consumption, inactive persistent facts, revoked onboarding
authority and later callback checks continue to fail closed.

## Operator behavior

The packaged command is `liquent-oidc-admission-login`.

`new-decision-id` emits fresh opaque decision material. `apply` reads a private
database URL file and a private exact-shape JSON request. It emits only one of
these public outcomes:

- `bound` when provisioning and server-side binding are complete;
- `rejected` for a neutral authorization or eligibility absence;
- a detail-free conflict; or
- detail-free technical unavailability.

Identifiers, admission material, login state, provider values and database
details are not emitted. Request representations suppress every request field.

The intended controlled sequence is:

1. generate and retain one decision ID in private operator material;
2. start exactly one browser login and pause at Google;
3. apply the private request against the staging database;
4. continue the same browser login only after `bound`; and
5. verify the resulting callback and session separately.

Running `apply` before the browser login is safe: it may provision the
retry-stable admission but returns `rejected` because no pending login exists.
Repeating the same request after exactly one login starts binds the same
admission rather than creating another one.

## Security and persistence boundaries

The adapter uses row locking where supported and a conditional update for the
final ownership check. The admission and pending-login lookups occur in one
database transaction. Unsupported database dialects fail technically closed.

No public route, request schema or browser contract is widened. No secret,
internal identifier, admission handle or pending state is added to a URL,
header, form, cookie or response. No provider-side setting is changed.

This slice adds no user, workspace, membership, role or research-permission
creation. It does not grant management capability. The only runtime mutation
owned here is attaching an already authorized admission to one unambiguous
pending login transaction.

Persistent user and workspace IDs retain their existing stable,
non-reassignable and non-reusable meaning. Admission and login-transaction
retention continue to follow their established lower bounds; this slice does
not weaken or redefine them.

## Verification

The focused tests cover:

- binding without caller-selected state;
- exact retry behavior;
- neutral zero- and multiple-candidate outcomes;
- unknown and expired admission rejection;
- provision-before-login followed by retry and binding;
- one decision, one admission and one bound transaction;
- private exact-shape request loading and representation safety; and
- packaging of the operator entry point.

The end-to-end onboarding test is PostgreSQL-specific because the established
production authorization and provisioning stores rely on PostgreSQL locking.
SQLite remains a deterministic local contract fixture for the isolated binding
adapter.

## Explicit non-goals and next step

LQ-2646 does not execute staging admission, complete a Google callback, create
an external identity binding, issue a session, or validate the authenticated
application experience. It does not deploy, publish, promote or merge itself.

After review, release and staging promotion, the next controlled operation is
one real staging login using the sequence above. Its evidence should verify one
consumed admission, one persistent external identity binding and one valid
session without disclosing their values. Membership and research authorization
remain separate later work.
