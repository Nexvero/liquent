# Initial staging bootstrap and edge routing

This is a one-time, supervised bootstrap. It is not a production deployment.

## External prerequisites

1. Create `staging.liquent.ai` A/AAAA records only for explicitly enabled VPS
   addresses and wait for authoritative DNS propagation.
2. Obtain a certificate whose SAN covers `staging.liquent.ai`; place the full
   chain and private key under `/opt/liquent/edge/certs`. The key must be mode
   `0600` and never enter Git.
3. Configure `/etc/liquent/deploy.env` and a root-owned mode-`0600`
   `initial-staging.env` using the checked-in examples.
4. Prepare the released image digest, matching release manifest and fresh
   verified backup evidence.
5. Confirm the Edge and application share only the existing
   `liquent_public` network; PostgreSQL remains internal.

## Read-only gate

Run `preflight-initial-staging.sh` first. Normal mode verifies authoritative
host resolution against `EXPECTED_IPV4`; `--offline` exists only for local
contract testing and must not authorize a real bootstrap. The preflight also
checks certificate hostname coverage, certificate/private-key correspondence,
release evidence and file permissions.

## Apply gate

The operator must provide the literal `INITIALIZE-STAGING`. The bootstrap then
serializes against normal promotions, journals evidence, pulls by digest,
starts PostgreSQL, runs migrations, starts the Control Plane, installs the
reviewed Edge route, validates Nginx configuration and finally requires the
external HTTPS liveness response.

On failure, the Control Plane is stopped, the prior image environment and Edge
configuration are restored, and the run is marked failed. Database migrations
remain applied and must have backward-compatible semantics.

## Exposure contract

The Edge route exposes only `/health/live`. `/health/ready`, internal metrics,
API documentation and all other paths remain unavailable; unmatched HTTPS
requests return 404. HTTP redirects to HTTPS except for the container-local
`/healthz` endpoint.

After a successful bootstrap, retain the resulting digest as the first known
healthy rollback point and use only the normal LQ-066 promotion process.
