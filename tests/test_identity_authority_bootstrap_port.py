import inspect
from dataclasses import FrozenInstanceError, fields

import pytest

from liquent_platform.identity.access import UserId
from liquent_platform.identity.admission import IdentityAdmissionId
from liquent_platform.identity.bootstrap import BootstrappedIdentityAuthority
from liquent_platform.identity.ports import IdentityAuthorityBootstrapStore
from liquent_platform.identity.research import WorkspaceId
from liquent_platform.persistence.identity_errors import (
    IdentityAuthorityBootstrapUnavailable,
)


class Stub:
    def bootstrap_initial_identity(self) -> BootstrappedIdentityAuthority | None:
        return BootstrappedIdentityAuthority(
            UserId("user-1"), WorkspaceId("workspace-1"), IdentityAdmissionId("a-1")
        )


def test_result_is_frozen_slotted_hashable_and_repr_free() -> None:
    result = Stub().bootstrap_initial_identity()
    assert result is not None
    assert [item.name for item in fields(result)] == [
        "user_id",
        "workspace_id",
        "admission_id",
    ]
    assert all(not item.repr for item in fields(result))
    assert repr(result) == "BootstrappedIdentityAuthority()"
    assert hash(result)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        result.user_id = UserId("other")  # type: ignore[misc]


def test_port_has_the_exact_parameterless_operation() -> None:
    signature = inspect.signature(
        IdentityAuthorityBootstrapStore.bootstrap_initial_identity, eval_str=True
    )
    assert list(signature.parameters) == ["self"]
    assert signature.return_annotation == BootstrappedIdentityAuthority | None


def test_structural_implementation_satisfies_the_port() -> None:
    store: IdentityAuthorityBootstrapStore = Stub()
    assert store.bootstrap_initial_identity() is not None


def test_error_is_detail_free_and_takes_no_argument() -> None:
    error = IdentityAuthorityBootstrapUnavailable()
    assert error.args == ("identity_authority_bootstrap_unavailable",)
    assert error.code == "identity_authority_bootstrap_unavailable"
    with pytest.raises(TypeError):
        IdentityAuthorityBootstrapUnavailable("secret")  # type: ignore[call-arg]
