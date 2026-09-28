"""Atomic owner-private no-replace file for one pre-create launch binding."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import secrets
import stat

from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    EncodedManifestHandoffSupervisorLaunchDocument,
    ManifestHandoffSupervisorLaunchDocumentConflict,
    PublishedManifestHandoffSupervisorLaunchDocument,
    PublishManifestHandoffSupervisorLaunchDocument,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.identity.manifest_handoff_supervisor_runtime import (
    ManifestHandoffSupervisorControlDirectoryId,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)


_NAME = "launch-binding.json"
_MAXIMUM = 65_536


class AtomicLocalManifestHandoffSupervisorLaunchDocuments:
    __slots__ = ("_codec", "_identity", "_resolve", "_root")

    def __init__(
        self, root: Path, *,
        resolve_directory: Callable[[ManifestHandoffSupervisorControlDirectoryId], Path | None],
        codec: CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
        identity_policy: ManifestHandoffSupervisorLaunchIdentityPolicy | None = None,
    ) -> None:
        if (
            not isinstance(root, Path) or not root.is_absolute()
            or not callable(resolve_directory)
            or type(codec) is not CanonicalManifestHandoffSupervisorLaunchDocumentCodec
            or (identity_policy is not None
                and type(identity_policy) is not ManifestHandoffSupervisorLaunchIdentityPolicy)
        ):
            raise ManifestHandoffRegistryUnavailable
        if identity_policy is not None and identity_policy.host_owner_uid != os.geteuid():
            raise ManifestHandoffRegistryUnavailable
        self._root, self._resolve, self._codec = root, resolve_directory, codec
        self._identity = identity_policy

    def __repr__(self) -> str:
        return "AtomicLocalManifestHandoffSupervisorLaunchDocuments()"

    def publish(self, request):
        if type(request) is not PublishManifestHandoffSupervisorLaunchDocument:
            raise ManifestHandoffRegistryUnavailable
        encoded = request.document
        directory = self._directory(encoded.document.gate.control_directory_id)
        directory_fd = temporary_fd = None
        temporary = ".pending-launch-" + secrets.token_hex(16)
        try:
            directory_fd = self._open_directory(directory)
            current = self._read_optional(directory_fd)
            if current is not None:
                return self._same_or_conflict(encoded, current)
            temporary_fd = os.open(
                temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600, dir_fd=directory_fd,
            )
            if self._identity is not None:
                os.fchown(
                    temporary_fd, self._identity.host_owner_uid,
                    self._identity.reader_gid,
                )
                os.fchmod(temporary_fd, 0o640)
            _write_all(temporary_fd, encoded.content.value)
            os.fsync(temporary_fd)
            os.close(temporary_fd)
            temporary_fd = None
            try:
                os.link(
                    temporary, _NAME, src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd, follow_symlinks=False,
                )
            except FileExistsError:
                current = self._read(directory_fd)
                return self._same_or_conflict(encoded, current)
            finally:
                os.unlink(temporary, dir_fd=directory_fd)
                temporary = ""
            os.fsync(directory_fd)
            return self._published(encoded)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if temporary_fd is not None:
                os.close(temporary_fd)
            if directory_fd is not None:
                if temporary:
                    try:
                        os.unlink(temporary, dir_fd=directory_fd)
                    except FileNotFoundError:
                        pass
                os.close(directory_fd)

    def read(self, directory_id):
        if type(directory_id) is not ManifestHandoffSupervisorControlDirectoryId:
            raise ManifestHandoffRegistryUnavailable
        directory_fd = None
        try:
            directory_fd = self._open_directory(self._directory(directory_id))
            try:
                content = self._read(directory_fd)
            except FileNotFoundError:
                return None
            return self._codec.decode_content(content)
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if directory_fd is not None:
                os.close(directory_fd)

    def _same_or_conflict(
        self, encoded: EncodedManifestHandoffSupervisorLaunchDocument, current: bytes
    ):
        if current != encoded.content.value:
            return ManifestHandoffSupervisorLaunchDocumentConflict()
        if self._codec.decode_content(current) != encoded.document:
            raise ManifestHandoffRegistryUnavailable
        return self._published(encoded)

    @staticmethod
    def _published(encoded):
        return PublishedManifestHandoffSupervisorLaunchDocument(
            encoded.document.document_id, encoded.facts
        )

    def _directory(self, directory_id):
        try:
            path = self._resolve(directory_id)
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        if not isinstance(path, Path) or not path.is_absolute() or path.parent != self._root:
            raise ManifestHandoffRegistryUnavailable
        return path

    def _open_directory(self, path):
        root_fd = directory_fd = None
        try:
            root_fd = os.open(
                self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            directory_fd = os.open(
                path.name,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                dir_fd=root_fd,
            )
            facts = os.fstat(directory_fd)
            if (
                not stat.S_ISDIR(facts.st_mode) or facts.st_uid != os.geteuid()
                or stat.S_IMODE(facts.st_mode) != 0o700
            ):
                raise ManifestHandoffRegistryUnavailable
            return directory_fd
        except ManifestHandoffRegistryUnavailable:
            if directory_fd is not None:
                os.close(directory_fd)
            raise
        except Exception:
            if directory_fd is not None:
                os.close(directory_fd)
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if root_fd is not None:
                os.close(root_fd)

    def _read_optional(self, directory_fd):
        try:
            return self._read(directory_fd)
        except FileNotFoundError:
            return None

    def _read(self, directory_fd):
        descriptor = os.open(
            _NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd
        )
        try:
            facts = os.fstat(descriptor)
            identity = self._identity
            expected_uid = os.geteuid() if identity is None else identity.host_owner_uid
            expected_gid = facts.st_gid if identity is None else identity.reader_gid
            expected_mode = 0o600 if identity is None else 0o640
            if (
                not stat.S_ISREG(facts.st_mode) or facts.st_uid != expected_uid
                or facts.st_gid != expected_gid
                or stat.S_IMODE(facts.st_mode) != expected_mode or facts.st_nlink != 1
                or facts.st_size < 1 or facts.st_size > _MAXIMUM
            ):
                raise ManifestHandoffRegistryUnavailable
            content = bytearray()
            while len(content) <= _MAXIMUM:
                part = os.read(descriptor, min(8192, _MAXIMUM + 1 - len(content)))
                if not part:
                    break
                content.extend(part)
            if not content or len(content) > _MAXIMUM:
                raise ManifestHandoffRegistryUnavailable
            return bytes(content)
        finally:
            os.close(descriptor)


def _write_all(descriptor: int, content: bytes) -> None:
    offset = 0
    while offset < len(content):
        written = os.write(descriptor, content[offset:])
        if written <= 0:
            raise ManifestHandoffRegistryUnavailable
        offset += written
