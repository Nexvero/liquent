"""Neutral technical error of the persistent external-identity store."""


class ExternalIdentityStoreUnavailable(Exception):
    """Report that the identity store could not answer, without any detail.

    Kept apart from the neutral ``None`` of a business decision: an unreachable
    database, a transaction that cannot be completed safely, a stored record
    that violates the structural invariants, and an unusable clock are all
    technical, while an unknown, expired, or already consumed admission is not.

    It holds no identity, user, workspace, admission id, provisioning handle,
    SQL, table, constraint, driver, host, port, or DSN detail, so it reveals
    nothing about what exists or how the store is built.
    """

    code = "external_identity_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)
