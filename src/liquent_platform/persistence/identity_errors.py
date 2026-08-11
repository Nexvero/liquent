"""Neutral technical errors of the persistent external-identity store."""


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


class IdentityAdmissionProvisioningConflict(Exception):
    """Report that a provisioning handle was reused with different content.

    The same ProvisioningRequestId with the same business input is a retry and
    returns the stored admission id; with different content it is this contract
    violation, never resolved by overwriting the stored admission and never by
    creating a second one. Kept apart from technical unavailability: the stored
    state is intact and repeating changes nothing. It holds no handle,
    identifier, or storage detail, so it reveals neither what is stored nor
    what differed.
    """

    code = "identity_admission_provisioning_conflict"

    def __init__(self) -> None:
        super().__init__(self.code)


class IdentityAdmissionStoreUnavailable(Exception):
    """Report that admission provisioning could not be completed, detail-free.

    Raised when the operation could not be carried out at all or its outcome
    stays unclear — an unreachable database, a transaction that cannot complete
    safely, an unusable clock or id generator. It is neither a business
    decision nor a contract conflict: the authorized caller resolves it by
    repeating with the same handle, so at most one admission is ever created.
    It holds no handle, identifier, or storage detail, so it reveals nothing
    about what exists or how the store is built.
    """

    code = "identity_admission_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)
