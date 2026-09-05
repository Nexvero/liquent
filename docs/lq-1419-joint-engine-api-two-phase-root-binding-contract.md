# LQ-1419 Joint engine API two-phase root binding contract

- Acceptance record has one root check before and one after marker creation.
- Both checks bind the visible path to the held registry descriptor.
- The pre-create phase prevents writes after prior path detachment.
- The post-write phase prevents rebound paths from yielding success.
- Marker creation and readback remain between those two checks.
- Directory synchronization precedes the post-write phase.
- Both phases are mandatory and caller independent.
