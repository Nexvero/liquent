import inspect
from dataclasses import FrozenInstanceError
from datetime import timedelta

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import (
    IdentityAdmissionId,
    ProvisioningRequestId,
)
from liquent_platform.identity.ports import (
    ExternalIdentityAdmissionStore,
    IdentityAdmissionProvisioningStore,
)
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    IdentityAdmissionProvisioningConflict,
    IdentityAdmissionStoreUnavailable,
)


class _EqualToEverything(str):
    """A str subclass that redefines equality, so it must not be accepted."""

    def __eq__(self, other: object) -> bool:  # pragma: no cover - never called
        return True

    __hash__ = str.__hash__


class _MinimalProvisioningStore:
    """Structural stand-in only; real behaviour belongs to the adapter tests."""

    def provision_admission(
        self,
        request_id: ProvisioningRequestId,
        target_user_id: UserId,
        target_workspace_id: WorkspaceId,
        lifetime: timedelta,
    ) -> IdentityAdmissionId:
        return IdentityAdmissionId("admission-1")


@pytest.mark.parametrize(
    "raw",
    [
        "provisioning-request-1",
        "  Provisioning/Request//1  ",  # no trimming, casing, or normalization
        "x" * 512,
    ],
)
def test_valid_request_id_holds_the_exact_value(raw: str) -> None:
    request = ProvisioningRequestId(raw)

    assert request.value is raw


@pytest.mark.parametrize(
    "raw",
    [
        "",
        b"secret-provisioning-request",
        _EqualToEverything("secret-provisioning-request"),
    ],
)
def test_invalid_request_id_is_rejected_neutrally(raw: object) -> None:
    with pytest.raises(ValueError) as rejection:
        ProvisioningRequestId(raw)  # type: ignore[arg-type]

    # Exact text: the rejected handle is never echoed back to the caller.
    assert str(rejection.value) == "invalid provisioning request id"


def test_request_id_is_frozen_and_holds_only_its_value() -> None:
    request = ProvisioningRequestId("provisioning-request-1")

    assert ProvisioningRequestId.__slots__ == ("value",)
    with pytest.raises(FrozenInstanceError):
        request.value = "other"  # type: ignore[misc]


def test_request_id_is_hashable_and_hides_its_value_in_repr() -> None:
    request = ProvisioningRequestId("secret-provisioning-request")

    assert {request: 1}[ProvisioningRequestId("secret-provisioning-request")] == 1
    # The handle must not reach logs or traces through an object representation.
    assert "secret-provisioning-request" not in repr(request)
    assert "ProvisioningRequestId" in repr(request)


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        (
            IdentityAdmissionProvisioningConflict,
            "identity_admission_provisioning_conflict",
        ),
        (
            IdentityAdmissionStoreUnavailable,
            "identity_admission_store_unavailable",
        ),
    ],
)
def test_admission_error_is_neutral_and_takes_no_detail(
    error_type: type[Exception], code: str
) -> None:
    error = error_type()

    assert error.code == code  # type: ignore[attr-defined]
    assert error.args == (code,)
    assert str(error) == code
    with pytest.raises(TypeError):
        error_type("secret-provisioning-request")  # type: ignore[call-arg]


def test_admission_errors_are_distinct_exception_types() -> None:
    assert issubclass(IdentityAdmissionProvisioningConflict, Exception)
    assert issubclass(IdentityAdmissionStoreUnavailable, Exception)
    assert not issubclass(
        IdentityAdmissionStoreUnavailable, IdentityAdmissionProvisioningConflict
    )
    assert not issubclass(
        IdentityAdmissionProvisioningConflict, IdentityAdmissionStoreUnavailable
    )


def test_minimal_stub_satisfies_the_provisioning_port() -> None:
    port: IdentityAdmissionProvisioningStore = _MinimalProvisioningStore()

    admission_id = port.provision_admission(
        ProvisioningRequestId("provisioning-request-1"),
        UserId("user-1"),
        WorkspaceId("workspace-1"),
        timedelta(hours=1),
    )

    assert admission_id == IdentityAdmissionId("admission-1")


def test_provision_admission_signature_is_exact() -> None:
    signature = inspect.signature(
        IdentityAdmissionProvisioningStore.provision_admission, eval_str=True
    )
    parameters = list(signature.parameters.values())

    assert [parameter.name for parameter in parameters] == [
        "self",
        "request_id",
        "target_user_id",
        "target_workspace_id",
        "lifetime",
    ]
    assert [parameter.annotation for parameter in parameters[1:]] == [
        ProvisioningRequestId,
        UserId,
        WorkspaceId,
        timedelta,
    ]
    assert signature.return_annotation is IdentityAdmissionId
    assert all(
        parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
        and parameter.default is inspect.Parameter.empty
        for parameter in parameters[1:]
    )


def test_runtime_admission_store_is_unchanged() -> None:
    # Provisioning is a separate administrative port, not a widened runtime one.
    declared = {
        name
        for name in vars(ExternalIdentityAdmissionStore)
        if not name.startswith("_")
    }

    assert declared == {"consume_admission_and_bind"}
