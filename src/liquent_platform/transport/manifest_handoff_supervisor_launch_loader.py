"""Bounded read-only loader for one externally anchored wrapper launch file."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat

from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocumentExpectation,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_identity import (
    ManifestHandoffSupervisorLaunchIdentityPolicy,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)


_NAME = "launch-binding.json"
_MAXIMUM = 65_536


class ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader:
    __slots__ = ("_codec", "_identity", "_root")

    def __init__(self, root: Path, *,
                 codec: CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
                 identity_policy: ManifestHandoffSupervisorLaunchIdentityPolicy) -> None:
        if (not isinstance(root, Path) or not root.is_absolute()
                or type(codec) is not CanonicalManifestHandoffSupervisorLaunchDocumentCodec
                or type(identity_policy) is not ManifestHandoffSupervisorLaunchIdentityPolicy):
            raise ManifestHandoffRegistryUnavailable
        self._root = root
        self._codec = codec
        self._identity = identity_policy

    def __repr__(self) -> str:
        return "ReadOnlyManifestHandoffSupervisorLaunchDocumentLoader()"

    def load(self, expectation):
        if type(expectation) is not ManifestHandoffSupervisorLaunchDocumentExpectation:
            raise ManifestHandoffRegistryUnavailable
        directory_fd = descriptor = None
        try:
            directory_fd = os.open(
                self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            )
            descriptor = os.open(
                _NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=directory_fd
            )
            facts = os.fstat(descriptor)
            if (not stat.S_ISREG(facts.st_mode)
                    or facts.st_uid != self._identity.host_owner_uid
                    or facts.st_gid != self._identity.reader_gid
                    or stat.S_IMODE(facts.st_mode) != 0o640
                    or facts.st_nlink != 1 or facts.st_size < 1
                    or facts.st_size > _MAXIMUM):
                raise ManifestHandoffRegistryUnavailable
            content = _read_all(descriptor)
            if hashlib.sha256(content).hexdigest() != expectation.digest.value:
                raise ManifestHandoffRegistryUnavailable
            document = self._codec.decode_content(content)
            gate = document.gate
            if not all((
                document.document_id == expectation.document_id,
                document.creation_id == expectation.creation_id,
                gate.handle_id == expectation.handle_id,
                gate.control_directory_id == expectation.control_directory_id,
                document.image_digest == expectation.image_digest,
                gate.profile is expectation.profile,
            )):
                raise ManifestHandoffRegistryUnavailable
            return document
        except ManifestHandoffRegistryUnavailable:
            raise
        except Exception:
            raise ManifestHandoffRegistryUnavailable from None
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if directory_fd is not None:
                os.close(directory_fd)


def _read_all(descriptor: int) -> bytes:
    content = bytearray()
    while len(content) <= _MAXIMUM:
        part = os.read(descriptor, min(8192, _MAXIMUM + 1 - len(content)))
        if not part:
            break
        content.extend(part)
    if not content or len(content) > _MAXIMUM:
        raise ManifestHandoffRegistryUnavailable
    return bytes(content)
