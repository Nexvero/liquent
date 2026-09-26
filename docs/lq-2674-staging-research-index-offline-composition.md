# LQ-2674 – Staging Research-index offline composition

## Result

LQ-2674 composes the pure LQ-2671 request plan, LQ-2672 response classifier,
LQ-2673 reducer, and LQ-2668 evaluator into one offline application function.

It receives a validated run and exactly nine already acquired bounded response
containers. It performs no network access, authentication, file access,
persistence, mutation, deployment, or promotion.

## Closed pipeline

The composition generates the canonical request plan internally, pairs it with
the exact response tuple, classifies each pair, reduces the two revocation
phases, and evaluates the resulting eight observations.

Lists, missing responses, and additional responses are rejected before any
result is produced. Response mismatch remains rejection; malformed response
material remains technical unavailability.

Only the established acceptance result leaves the function. Raw response,
credential, identity, workspace, JobId, provider, and diagnostic data are not
retained in the result.

## Verification

Tests prove end-to-end offline acceptance, rejection, unavailability, exact
cardinality, tuple-only input, and preservation of the validated run binding.

## Explicit non-goals

This slice adds no HTTP transport, credential loader, session store, evidence
file, CLI, workflow, retry, redirect following, revocation mutation,
deployment, promotion, rollback, schema, migration, route, image, secret, or
installed operator.

## Next step

A later acquisition adapter may execute the closed plan using separately
provisioned credential slots and supply bounded responses to this composition.
Credential persistence, revocation coordination, evidence writing, live
staging execution, and promotion remain separate decisions.
