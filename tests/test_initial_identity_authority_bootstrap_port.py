from liquent_platform.identity.access import BootstrappedIdentityAuthority, UserId
from liquent_platform.identity.ports import InitialIdentityAuthorityBootstrap
from liquent_platform.identity.research import WorkspaceId


class StubBootstrap:
    def bootstrap(self) -> BootstrappedIdentityAuthority | None:
        return BootstrappedIdentityAuthority(
            UserId("user-1"), WorkspaceId("workspace-1")
        )


def _bootstrap(
    port: InitialIdentityAuthorityBootstrap,
) -> BootstrappedIdentityAuthority | None:
    return port.bootstrap()


def test_port_accepts_no_caller_selected_identity_or_authority() -> None:
    assert _bootstrap(StubBootstrap()) == BootstrappedIdentityAuthority(
        UserId("user-1"), WorkspaceId("workspace-1")
    )
