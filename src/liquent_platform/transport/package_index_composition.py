"""Owner-only credential loading and local package-index composition."""

from __future__ import annotations

import os
import stat
import time
from collections.abc import Callable
from pathlib import Path

import httpx2

from liquent_platform.identity.release_publication_package_index import (
    PackageIndexReleasePublicationAdapter,
)
from liquent_platform.identity.release_publication_provider import (
    PackageIndexHttpPolicy,
    PackageIndexProviderConfiguration,
    ReleasePublicationProviderUnavailable,
)
from liquent_platform.transport.package_index import (
    HttpPackageIndexProviderTransport,
)


_CREDENTIAL_MAX_BYTES = 4096


class OwnerOnlyPackageIndexCredentialSource:
    """Read one bounded credential from an owner-only regular file."""

    __slots__ = ("_path",)

    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or not path.is_absolute():
            raise ValueError("package index credential path must be absolute")
        self._path = path

    def __repr__(self) -> str:
        return "OwnerOnlyPackageIndexCredentialSource()"

    def load_credential(self) -> str:
        descriptor: int | None = None
        try:
            no_follow = getattr(os, "O_NOFOLLOW", None)
            close_on_exec = getattr(os, "O_CLOEXEC", None)
            if no_follow is None or close_on_exec is None:
                raise ReleasePublicationProviderUnavailable
            descriptor = os.open(
                self._path,
                os.O_RDONLY | no_follow | close_on_exec,
            )
            metadata = os.fstat(descriptor)
            mode = stat.S_IMODE(metadata.st_mode)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or metadata.st_nlink != 1
                or mode not in {0o400, 0o600}
                or metadata.st_size > _CREDENTIAL_MAX_BYTES + 1
            ):
                raise ReleasePublicationProviderUnavailable
            value = os.read(descriptor, _CREDENTIAL_MAX_BYTES + 2)
            if len(value) > _CREDENTIAL_MAX_BYTES + 1:
                raise ReleasePublicationProviderUnavailable
            if value.endswith(b"\n"):
                value = value[:-1]
            credential = value.decode("utf-8")
            PackageIndexProviderConfiguration(
                "https://credential-validation.invalid",
                "credential-validation",
                credential,
            )
            return credential
        except ReleasePublicationProviderUnavailable:
            raise
        except Exception:
            raise ReleasePublicationProviderUnavailable from None
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass


class PackageIndexPublicationComposition:
    """Own one controlled client and expose one configured adapter."""

    __slots__ = ("_client", "publication")

    def __init__(
        self,
        client: httpx2.Client,
        publication: PackageIndexReleasePublicationAdapter,
    ) -> None:
        self._client: httpx2.Client | None = client
        self.publication = publication

    def __repr__(self) -> str:
        return "PackageIndexPublicationComposition()"

    def __enter__(self) -> PackageIndexPublicationComposition:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        client, self._client = self._client, None
        if client is not None:
            try:
                client.close()
            except Exception:
                raise ReleasePublicationProviderUnavailable from None


def compose_package_index_publication(
    *,
    origin: str,
    target_name: str,
    credential_path: Path,
    policy: PackageIndexHttpPolicy,
    monotonic: Callable[[], float] = time.monotonic,
    client_factory: Callable[..., httpx2.Client] = httpx2.Client,
) -> PackageIndexPublicationComposition:
    """Load current local authority and build one wholly owned dependency group.

    Construction reads only the credential file. It performs no provider request
    and does not attach the resulting adapter to any CLI or production process.
    """

    if type(policy) is not PackageIndexHttpPolicy:
        raise ValueError("package index HTTP policy is required")
    credential = OwnerOnlyPackageIndexCredentialSource(
        credential_path
    ).load_credential()
    configuration = PackageIndexProviderConfiguration(
        origin, target_name, credential
    )
    client: httpx2.Client | None = None
    try:
        client = client_factory(
            trust_env=False,
            follow_redirects=False,
            limits=httpx2.Limits(
                max_connections=1,
                max_keepalive_connections=1,
                keepalive_expiry=5.0,
            ),
        )
        if type(client) is not httpx2.Client:
            raise ReleasePublicationProviderUnavailable
        transport = HttpPackageIndexProviderTransport(client, policy, monotonic)
        publication = PackageIndexReleasePublicationAdapter(
            configuration, transport
        )
        return PackageIndexPublicationComposition(client, publication)
    except ReleasePublicationProviderUnavailable:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        raise
    except Exception:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass
        raise ReleasePublicationProviderUnavailable from None
