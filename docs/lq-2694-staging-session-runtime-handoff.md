# LQ-2694 — Staging session runtime handoff

LQ-2694 binds the controlled LQ-2693 acquisition to the existing LQ-2689
operator. A caller supplies only the opaque session-set identity and its exact
expected revision alongside the already bounded acceptance-run facts. The
operator resolves the persistent registry, acquires the validated handoff, and
only then starts the existing runtime.

Neutral absence before, during, or after acquisition returns neutral absence
and performs no acceptance execution. Registry, acquisition, composition, and
runtime failures collapse to one detail-free technical-unavailability signal.
The acquired session handoff remains identification material and grants no
authority; all fixture authority continues to resolve from the system of
record at the existing mutation boundary.

This slice adds no session, credential, user, workspace, membership, role, or
capability creation or mutation. It chooses no provider, login automation,
secret source, CLI, deployment, or promotion mechanism. Concrete acquisition
and real staging promotion remain separate later work.
