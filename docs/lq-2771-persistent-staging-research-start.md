# LQ-2771 — Persistent staging Research start

LQ-2771 closes the persistence gap found during the controlled staging
acceptance of LQ-2770. A database-backed Control Plane no longer executes an
accepted Research job synchronously in process. It validates the authenticated
request and queues one durable job for the separately deployed Research worker.

The public request job ID is used as the retry-safe acceptance ID. The response
contains the generated durable job ID that must be used for status and evidence
reads. Current workspace membership and `research:write` are checked before any
dataset resolution; the persistent acceptance checks the authority again in the
same transaction that creates the job. Revocation therefore prevents new jobs,
and the worker also invalidates queued work whose authority no longer exists.

Database-backed status reads expose the accepted experiment identity without
returning claims, leases or worker details. Successful evidence is read from the
durable outcome row and remains available only while the actor has current
`research:read` or `research:write` authority. Missing, unauthorized and failed
outcomes remain detail-poor.

This slice does not grant a permission, create a membership, deploy an image or
run a staging job. A subsequent immutable staging release must still prove one
worker claim, one durable outcome, artifact integrity and immediate removal of
the temporary `research:write` permission.
