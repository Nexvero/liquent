"""Complete inert dependency composition for local Engine API proxy health."""

from __future__ import annotations

from dataclasses import dataclass

from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_client_peer import (
    LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_composition import (
    ManifestHandoffSupervisorEngineApiProcessBundle,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_authority import (
    ManifestHandoffSupervisorEngineApiHealthSocketAuthority,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_protocol import (
    ClosedManifestHandoffSupervisorEngineApiHealthProtocol,
)
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_process_owner import (
    ManifestHandoffSupervisorEngineApiProcessOwner,
)


@dataclass(frozen=True, slots=True)
class ManifestHandoffSupervisorEngineApiHealthBundle:
    process_bundle: ManifestHandoffSupervisorEngineApiProcessBundle
    authority: ManifestHandoffSupervisorEngineApiHealthSocketAuthority
    owner: ManifestHandoffSupervisorEngineApiProcessOwner
    peer_policy: LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
    protocol: ClosedManifestHandoffSupervisorEngineApiHealthProtocol

    def __post_init__(self) -> None:
        if (
            type(self.process_bundle) is not ManifestHandoffSupervisorEngineApiProcessBundle
            or type(self.authority) is not ManifestHandoffSupervisorEngineApiHealthSocketAuthority
            or type(self.owner) is not ManifestHandoffSupervisorEngineApiProcessOwner
            or type(self.peer_policy) is not LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy
            or type(self.protocol) is not ClosedManifestHandoffSupervisorEngineApiHealthProtocol
            or self.owner._bundle is not self.process_bundle
            or self.protocol._owner is not self.owner
            or self.peer_policy._socket is not self.authority.socket_path
            or self.peer_policy._uid != self.authority.peer_uid
            or self.peer_policy._gid != self.authority.peer_gid
            or self.peer_policy._timeout != float(self.authority.timeout_seconds)
        ):
            raise ManifestHandoffRegistryUnavailable

    def __repr__(self) -> str:
        return "ManifestHandoffSupervisorEngineApiHealthBundle()"


def compose_manifest_handoff_supervisor_engine_api_health(
    process_bundle: ManifestHandoffSupervisorEngineApiProcessBundle,
    authority: ManifestHandoffSupervisorEngineApiHealthSocketAuthority,
) -> ManifestHandoffSupervisorEngineApiHealthBundle:
    """Build one complete health graph without reading or mutating host state."""
    try:
        if (
            type(process_bundle) is not ManifestHandoffSupervisorEngineApiProcessBundle
            or type(authority) is not ManifestHandoffSupervisorEngineApiHealthSocketAuthority
        ):
            raise ManifestHandoffRegistryUnavailable
        owner = ManifestHandoffSupervisorEngineApiProcessOwner(process_bundle)
        peer_policy = authority.client_peer_policy()
        protocol = ClosedManifestHandoffSupervisorEngineApiHealthProtocol(owner)
        return ManifestHandoffSupervisorEngineApiHealthBundle(
            process_bundle, authority, owner, peer_policy, protocol
        )
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None
