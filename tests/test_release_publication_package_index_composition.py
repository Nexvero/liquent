import os
from datetime import timedelta
from pathlib import Path

import httpx2
import pytest

from liquent_platform.identity.release_publication_provider import (
    PackageIndexHttpPolicy,
    ReleasePublicationProviderUnavailable,
)
from liquent_platform.transport.package_index_composition import (
    OwnerOnlyPackageIndexCredentialSource,
    compose_package_index_publication,
)


POLICY = PackageIndexHttpPolicy(
    timedelta(seconds=1),
    timedelta(seconds=1),
    timedelta(seconds=2),
    4096,
    16384,
)


def _credential(tmp_path: Path, value: bytes = b"short-lived-token\n") -> Path:
    path = tmp_path / "package-index-credential"
    path.write_bytes(value)
    path.chmod(0o600)
    return path


@pytest.mark.parametrize("mode", [0o400, 0o600])
def test_owner_only_source_loads_bounded_utf8_and_one_terminal_lf(
    tmp_path: Path, mode: int
) -> None:
    path = _credential(tmp_path)
    path.chmod(mode)
    try:
        source = OwnerOnlyPackageIndexCredentialSource(path)
        assert source.load_credential() == "short-lived-token"
        assert repr(source) == "OwnerOnlyPackageIndexCredentialSource()"
    finally:
        path.chmod(0o600)


@pytest.mark.parametrize("mode", [0o000, 0o200, 0o640, 0o700])
def test_source_rejects_every_non_owner_read_only_mode(
    tmp_path: Path, mode: int
) -> None:
    path = _credential(tmp_path)
    path.chmod(mode)
    try:
        with pytest.raises(ReleasePublicationProviderUnavailable) as caught:
            OwnerOnlyPackageIndexCredentialSource(path).load_credential()
        assert str(caught.value) == "release_publication_provider_unavailable"
    finally:
        path.chmod(0o600)


def test_source_rejects_symlink_directory_and_relative_path(tmp_path: Path) -> None:
    path = _credential(tmp_path)
    link = tmp_path / "credential-link"
    link.symlink_to(path)
    for rejected in (link, tmp_path):
        with pytest.raises(ReleasePublicationProviderUnavailable):
            OwnerOnlyPackageIndexCredentialSource(rejected).load_credential()
    with pytest.raises(ValueError):
        OwnerOnlyPackageIndexCredentialSource(Path("relative"))


@pytest.mark.parametrize(
    "value",
    [b"", b" token", b"token ", b"token\nagain", b"token\r\n", b"\xff"],
)
def test_source_rejects_invalid_content_without_disclosure(
    tmp_path: Path, value: bytes
) -> None:
    path = _credential(tmp_path, value)
    with pytest.raises(ReleasePublicationProviderUnavailable) as caught:
        OwnerOnlyPackageIndexCredentialSource(path).load_credential()
    assert str(caught.value) == "release_publication_provider_unavailable"
    assert "token" not in repr(caught.value)
    assert str(path) not in repr(caught.value)


def test_source_rejects_oversize_before_returning_content(tmp_path: Path) -> None:
    path = _credential(tmp_path, b"x" * 4097)
    with pytest.raises(ReleasePublicationProviderUnavailable):
        OwnerOnlyPackageIndexCredentialSource(path).load_credential()


def test_composition_builds_one_restricted_owned_client_without_network(
    tmp_path: Path,
) -> None:
    path = _credential(tmp_path)
    seen = {}

    def factory(**arguments):
        seen.update(arguments)
        return httpx2.Client(
            transport=httpx2.MockTransport(
                lambda _: pytest.fail("composition performed provider I/O")
            ),
            **arguments,
        )

    composition = compose_package_index_publication(
        origin="https://packages.example",
        target_name="stable",
        credential_path=path,
        policy=POLICY,
        client_factory=factory,
    )
    client = composition._client
    assert seen["trust_env"] is False
    assert seen["follow_redirects"] is False
    assert seen["limits"].max_connections == 1
    assert seen["limits"].max_keepalive_connections == 1
    assert repr(composition) == "PackageIndexPublicationComposition()"
    assert "token" not in repr(composition.publication)
    composition.close()
    assert client is not None and client.is_closed
    composition.close()


def test_context_manager_closes_the_owned_client(tmp_path: Path) -> None:
    path = _credential(tmp_path)
    created = []

    def factory(**arguments):
        client = httpx2.Client(
            transport=httpx2.MockTransport(lambda _: httpx2.Response(404)),
            **arguments,
        )
        created.append(client)
        return client

    with compose_package_index_publication(
        origin="https://packages.example",
        target_name="stable",
        credential_path=path,
        policy=POLICY,
        client_factory=factory,
    ) as composition:
        assert composition.publication is not None
        assert not created[0].is_closed
    assert created[0].is_closed


def test_client_construction_failure_is_detail_free(tmp_path: Path) -> None:
    path = _credential(tmp_path)

    def fail(**_):
        raise RuntimeError("provider-secret-detail")

    with pytest.raises(ReleasePublicationProviderUnavailable) as caught:
        compose_package_index_publication(
            origin="https://packages.example",
            target_name="stable",
            credential_path=path,
            policy=POLICY,
            client_factory=fail,
        )
    assert str(caught.value) == "release_publication_provider_unavailable"
    assert "provider-secret-detail" not in repr(caught.value)


def test_source_opens_with_no_follow_and_close_on_exec(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _credential(tmp_path)
    original = os.open
    seen = []

    def record(target, flags):
        seen.append(flags)
        return original(target, flags)

    monkeypatch.setattr(os, "open", record)
    assert OwnerOnlyPackageIndexCredentialSource(path).load_credential()
    assert seen[0] & os.O_NOFOLLOW
    assert seen[0] & os.O_CLOEXEC
