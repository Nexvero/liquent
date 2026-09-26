# LQ-2669 – Staging Research-index acceptance offline tool

## Result

LQ-2669 adds a repository-local offline tool for the LQ-2668 evaluator.

It reads one already sanitized observation document and emits one minimal
bound result. It performs no network request and holds no staging credential,
authority, or mutation capability.

## Frozen package boundary

The tool lives under `tools/` and is not a Python package console entry point.
The intentionally frozen inventory of 72 installed operators remains exactly
unchanged, as do wheel entry-point verification and release bundle scope.

## Input boundary

`--input` must name an owner-private regular file, not a symbolic link. Empty
files, files larger than 16 KiB, malformed JSON, unknown fields, malformed
observations, or invalid run binding fail closed.

Cookies, tokens, response bodies, identities, JobIds, diagnostics, and
provider data are not valid input fields.

## Output and status

Canonical output contains only candidate digest, staging origin, observation
time, and overall outcome.

Exit code 0 means accepted, 3 rejected, 4 unavailable, and 2 invalid or
unreadable input. Input failures emit no result or private detail.

The output is evidence for a later authority decision. It does not authorize
or trigger promotion.

## Verification

Tests prove minimal output, distinct classification codes, private regular-file
enforcement, symlink rejection, closed input shape, and secret non-reflection.
The frozen operator and wheel inventories remain green.

## Explicit non-goals

This slice does not acquire observations, authenticate, call staging, follow
redirects, write evidence, mutate authority, deploy, promote, roll back, or
repair an environment.

It adds no installed command, package operator, schema, migration, route, edge
configuration, image, service, timer, workflow, DNS, TLS, OIDC, or secret.

## Next step

A later separately authorized acquisition slice may produce sanitized input
from real staging. Actual promotion remains blocked until repository and image
gates pass and release authority accepts the evidence.
