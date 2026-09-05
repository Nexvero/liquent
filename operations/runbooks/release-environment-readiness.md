# Release environment readiness evidence checklist

This checklist is an offline approval gate before the first real package
provider access in one environment. It does not contact DNS, TLS, a provider,
credential store, database, deployment system, or application runtime.

Completing the checklist does not itself publish, deploy, grant product
authority, or authorize an automatic start. The environment's independent
review process owns the final decision.

## Handling rules

- Work only in the approved restricted evidence record.
- Use stable opaque evidence references and lowercase SHA-256 digests.
- Never attach credentials, secret-manager paths, DSNs, Authorization headers,
  local private paths, provider response bodies, private keys, or request files.
- Record UTC timestamps with timezone and identify the exact review revision.
- Do not mark an item complete when its evidence is missing, expired,
  inaccessible, ambiguous, or covers a different environment.
- A copied decision from staging or another target is not Production evidence.

## Bound scope

Record all values before review:

- [ ] Stable readiness decision ID.
- [ ] Exact environment and responsible operating boundary.
- [ ] Canonical HTTPS origin with no alias, mirror, fallback, or redirect target.
- [ ] Package name exactly `liquent`.
- [ ] Exact provider target name.
- [ ] Non-secret credential identity and issuing boundary.
- [ ] Application version and immutable Operational Bundle SHA-256.
- [ ] Publication host identity and dedicated process-account identity.
- [ ] Review revision, `valid_from` and mandatory `review_by` UTC timestamps.

Any change to a bound value starts a new review. Never edit an approved record
in place to follow a changed origin, credential, host, bundle, or target.

## Provider and package ownership review

Attach stable references and SHA-256 digests for evidence confirming:

- [ ] The provider account controls package name `liquent`.
- [ ] The target exists and has the intended visibility and immutability policy.
- [ ] Namespace reservation and typo-conflict review are complete.
- [ ] GET absence is represented by `404`.
- [ ] Create-only PUT cannot replace an existing equal or different version.
- [ ] Success uses `201` with only the expected provider-request identifier.
- [ ] GET read-back exposes canonical artifact ID, provider revision, package,
      version, wheel SHA-256, and visibility.
- [ ] Redirects, unexpected statuses, encodings, media types, and oversized
      responses fail closed.
- [ ] Quota, package-size limit, rate limit, and visibility latency cover one
      bounded GET/PUT/GET sequence and later read-only reconciliation.

The evidence must come from provider documentation, account configuration, or
a provider-representative non-Production environment. Do not perform a
Production test upload for this checklist.

## Credential review

Attach evidence references and digests confirming:

- [ ] Scope is limited to read and create for exactly the bound package/target.
- [ ] Credential cannot replace, delete, yank, administer users, sign releases,
      access databases, deploy applications, or manage OIDC.
- [ ] Credential is delivered only to the dedicated Publication account through
      an owner-only source accepted by the existing operator.
- [ ] Issuance, expiry, rotation, revocation, and emergency disable paths exist.
- [ ] Monitoring and support systems redact the credential and Authorization
      header.

Record only credential identity, scope summary, evidence reference, digest and
review time. Never record the secret or secret-manager locator.

## TLS, DNS, and egress review

Attach evidence references and digests confirming:

- [ ] TLS certificate verification remains enabled without a bypass.
- [ ] Certificate hostname coverage matches the exact bound origin.
- [ ] System trust path is compatible with the current client, which accepts no
      caller-configured CA bundle.
- [ ] No transparent TLS interception or environment-derived proxy is required.
- [ ] DNS ownership and expected provider addressing are reviewed.
- [ ] Egress is restricted to the bound provider and required database path.
- [ ] Redirects, alternate hosts, mirrors, and fallback origins are blocked.
- [ ] Certificate, DNS, trust-path, proxy, and egress changes trigger re-review.

This review is based on protected infrastructure evidence. The offline gate
does not resolve a hostname or open a socket.

## Publication host review

Attach evidence references and digests confirming:

- [ ] Dedicated non-interactive account and owner-only input directories.
- [ ] Exact application version, 42-migration head `20260826_0042`, 71 Console
      Entry Points, and 71 packaged modules including the package initializer.
- [ ] Database and provider network boundaries are independently restricted.
- [ ] Wall clock and monotonic clock health are monitored.
- [ ] Private storage is sufficient for retained immutable artifacts.
- [ ] Shell tracing, core dumps, broad HTTP/SQL debug logs, and secret-capturing
      diagnostics are disabled.
- [ ] HTTP application and deployment startup cannot access Publication
      credentials or invoke offline Release operators.

## Monitoring and incident review

Attach evidence references and digests confirming:

- [ ] Telemetry is limited to environment, process timing, exit code, outcome
      family, and approved stable references.
- [ ] Credential, DSN, local paths, provider body, signature bytes, registry
      inventory, and private requests are excluded.
- [ ] Named incident route covers timeout, output loss, provider outage,
      credential suspicion, hash conflict, and visibility delay.
- [ ] Possible PUT effect is always treated as Unknown Outcome.
- [ ] The response preserves the same Handoff-, Execution-, Attempt-, and
      Artifact references and uses supervised read-only reconciliation.
- [ ] Manual replacement upload, new Execution-ID, automatic retry, delete,
      yank, or replace is prohibited by this procedure.
- [ ] Credential revocation and egress isolation can stop later starts.

## Deployment separation review

Attach evidence references and digests confirming:

- [ ] Package Publication does not trigger an application deployment.
- [ ] Application deployment binds its own immutable digest and configuration.
- [ ] Migration readiness, backup/restore evidence, health checks, and rollback
      boundary are reviewed by the deployment process.
- [ ] Application rollback does not withdraw a published package.
- [ ] Package delete, yank, replace, or withdrawal requires a separate contract.

## Independent reviewer attestations

Record four distinct attestations:

1. Provider/package owner: actor reference, decision, UTC time, evidence-set
   digest and review revision.
2. Security reviewer: actor reference, decision, UTC time, evidence-set digest
   and review revision.
3. Operations reviewer: actor reference, decision, UTC time, evidence-set
   digest and review revision.
4. Release reviewer: actor reference, decision, UTC time, complete record digest
   and review revision.

The actor references must identify distinct review perspectives according to
the environment's separation-of-duties policy. They are not application roles
or Publication authorities.

No reviewer may attest an evidence-set digest different from the set retained
for the final record. A changed evidence byte invalidates the affected
attestation.

## Offline completeness audit

Before deciding readiness, a reviewer who did not prepare the record confirms:

- [ ] Every checkbox is resolved without `unknown`, placeholder, or inherited
      value.
- [ ] Every evidence reference is reachable in the restricted record.
- [ ] Every retained evidence object matches its recorded lowercase SHA-256.
- [ ] All evidence covers the same environment, origin, package, target,
      credential identity, host, account, and bundle.
- [ ] All four attestations cover the same final evidence-set digest and review
      revision.
- [ ] `valid_from` is not in the future and `review_by` has not passed.
- [ ] No revocation, credential rotation, scope change, host change, TLS/DNS
      change, provider behavior change, or newer conflicting decision exists.
- [ ] The final record contains no secret, DSN, local path, provider body, or
      authorization material.

The audit is entirely read-only. Do not use a failed completeness check as a
reason to query Production systems from the Publication host.

## Detail-free outcome

Record and disclose only one outcome outside the restricted evidence record:

- `approved`: complete, current, matching evidence and all reviews approve the
  exact bound scope;
- `rejected`: at least one review explicitly rejects the scope;
- `expired`: the review window ended or a bound fact changed;
- `revoked`: a later retained decision blocks new starts;
- `unavailable`: required evidence cannot be safely evaluated.

Do not disclose which credential, network, reviewer, provider, or host check
caused a non-approved result. Detailed reasons remain in the restricted record.

Only `approved` permits a separately supervised invocation under the existing
Publication runbook. It does not start that invocation.

## Retention and revalidation

Retain the bound scope, evidence objects, digests, attestations, decision,
validity window, supersession links, and revocation history for the applicable
Release, Incident, and Audit periods.

Revalidate immediately before a real operator start. Any expired, revoked,
unavailable, mismatched, or superseded record fails closed and requires no
provider contact to reach that result.
