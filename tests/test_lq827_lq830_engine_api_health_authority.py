from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority as authority_module
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import (
    ManifestHandoffSupervisorEngineApiHealthSocketAuthority,
)


def values(**changes):
    current = {
        "socket_path": Path("/run/liquent/health.sock"),
        "socket_uid": 10001,
        "socket_gid": 10002,
        "parent_uid": 10003,
        "parent_gid": 10004,
        "peer_uid": 10005,
        "peer_gid": 10006,
        "timeout_seconds": 5,
        "backlog": 8,
    }
    current.update(changes)
    return current


def test_complete_explicit_authority_is_frozen_and_detail_free() -> None:
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(**values())
    assert authority.socket_path == Path("/run/liquent/health.sock")
    assert authority.peer_uid == 10005
    with pytest.raises(FrozenInstanceError):
        authority.peer_uid = 1
    assert repr(authority) == "ManifestHandoffSupervisorEngineApiHealthSocketAuthority()"
    assert "health.sock" not in repr(authority)


@pytest.mark.parametrize("change", (
    {"socket_path": Path("relative.sock")},
    {"socket_path": Path("/")},
    {"socket_path": Path("/health.sock")},
    {"socket_path": Path("/run/../health.sock")},
    {"socket_path": "health.sock"},
    {"socket_uid": 0}, {"socket_gid": 0},
    {"parent_uid": 0}, {"parent_gid": 0},
    {"peer_uid": 0}, {"peer_gid": 0},
    {"peer_uid": True}, {"peer_gid": "10006"},
    {"timeout_seconds": 0}, {"timeout_seconds": 301},
    {"backlog": 0}, {"backlog": 129},
))
def test_noncanonical_path_identity_timeout_or_backlog_fails_closed(change) -> None:
    with pytest.raises(ManifestHandoffRegistryUnavailable):
        ManifestHandoffSupervisorEngineApiHealthSocketAuthority(**values(**change))


def test_authority_builds_exact_inert_kernel_peer_policy() -> None:
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(**values())
    policy = authority.client_peer_policy()
    assert type(policy) is LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
    assert policy._socket is authority.socket_path
    assert policy._uid == authority.peer_uid
    assert policy._gid == authority.peer_gid
    assert policy._timeout == 5.0


def test_socket_owner_parent_and_peer_identities_remain_independent() -> None:
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(**values())
    assert len({
        authority.socket_uid, authority.socket_gid,
        authority.parent_uid, authority.parent_gid,
        authority.peer_uid, authority.peer_gid,
    }) == 6


def test_peer_policy_construction_failure_is_detail_free(monkeypatch) -> None:
    monkeypatch.setattr(
        authority_module, "LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy",
        lambda **values: (_ for _ in ()).throw(RuntimeError("private detail")),
    )
    authority = ManifestHandoffSupervisorEngineApiHealthSocketAuthority(**values())
    with pytest.raises(ManifestHandoffRegistryUnavailable) as caught:
        authority.client_peer_policy()
    assert "private" not in str(caught.value)


def test_authority_has_no_listener_request_role_or_allow_surface() -> None:
    surface = vars(ManifestHandoffSupervisorEngineApiHealthSocketAuthority)
    for name in (
        "listen", "accept", "open", "close", "serve", "role", "allow",
        "authorize_request", "from_environment",
    ):
        assert name not in surface
