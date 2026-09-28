"""Owner-controlled immutable local storage for research result artifacts."""

from __future__ import annotations

import hashlib
import os
import re
import stat
import uuid
from pathlib import Path

from liquent_platform.application.ports import ArtifactReference


_KEY = re.compile(r"research/([0-9a-f]{64})/result\.json\Z")
_MEDIA_TYPE = "application/json"


class ResearchArtifactStoreUnavailable(Exception):
    code = "research_artifact_store_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


def _safe_directory(descriptor: int) -> None:
    metadata = os.fstat(descriptor)
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o022
    ):
        raise ResearchArtifactStoreUnavailable


class LocalImmutableResearchArtifactStore:
    """Create and verify canonical research JSON below one trusted root."""

    __slots__ = ("_root",)

    def __init__(self, root: Path) -> None:
        if not isinstance(root, Path) or not root.is_absolute():
            raise ValueError("research artifact root must be absolute")
        self._root = root
        descriptor: int | None = None
        try:
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            _safe_directory(descriptor)
        except ResearchArtifactStoreUnavailable:
            raise
        except Exception:
            raise ResearchArtifactStoreUnavailable from None
        finally:
            if descriptor is not None:
                os.close(descriptor)

    def __repr__(self) -> str:
        return "LocalImmutableResearchArtifactStore()"

    def put(self, *, key: str, content: bytes, media_type: str) -> ArtifactReference:
        try:
            digest = self._validate_input(key, content, media_type)
            parent, leaf = self._open_parent(key, create=True)
            try:
                existing = self._read_file(parent, leaf)
                if existing is not None:
                    if existing != content:
                        raise ResearchArtifactStoreUnavailable
                    return ArtifactReference(key, digest, media_type, len(content))
                temporary = f".result-{uuid.uuid4().hex}.tmp"
                descriptor: int | None = None
                try:
                    descriptor = os.open(
                        temporary,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=parent,
                    )
                    view = memoryview(content)
                    while view:
                        written = os.write(descriptor, view)
                        if written < 1:
                            raise ResearchArtifactStoreUnavailable
                        view = view[written:]
                    os.fsync(descriptor)
                    os.close(descriptor)
                    descriptor = None
                    try:
                        os.link(temporary, leaf, src_dir_fd=parent, dst_dir_fd=parent)
                    except FileExistsError:
                        if self._read_file(parent, leaf) != content:
                            raise ResearchArtifactStoreUnavailable
                    os.fsync(parent)
                finally:
                    if descriptor is not None:
                        os.close(descriptor)
                    try:
                        os.unlink(temporary, dir_fd=parent)
                    except FileNotFoundError:
                        pass
                return ArtifactReference(key, digest, media_type, len(content))
            finally:
                os.close(parent)
        except ResearchArtifactStoreUnavailable:
            raise
        except Exception:
            raise ResearchArtifactStoreUnavailable from None

    def get(self, reference: ArtifactReference) -> bytes:
        try:
            if type(reference) is not ArtifactReference:
                raise ResearchArtifactStoreUnavailable
            if (
                reference.media_type != _MEDIA_TYPE
                or type(reference.sha256) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", reference.sha256)
                or type(reference.size_bytes) is not int
                or reference.size_bytes < 1
            ):
                raise ResearchArtifactStoreUnavailable
            parent, leaf = self._open_parent(reference.key, create=False)
            try:
                content = self._read_file(parent, leaf)
            finally:
                os.close(parent)
            if (
                content is None
                or len(content) != reference.size_bytes
                or hashlib.sha256(content).hexdigest() != reference.sha256
            ):
                raise ResearchArtifactStoreUnavailable
            return content
        except ResearchArtifactStoreUnavailable:
            raise
        except Exception:
            raise ResearchArtifactStoreUnavailable from None

    @staticmethod
    def _validate_input(key: object, content: object, media_type: object) -> str:
        if type(key) is not str or _KEY.fullmatch(key) is None:
            raise ResearchArtifactStoreUnavailable
        if type(content) is not bytes or not content or media_type != _MEDIA_TYPE:
            raise ResearchArtifactStoreUnavailable
        return hashlib.sha256(content).hexdigest()

    def _open_parent(self, key: str, *, create: bool) -> tuple[int, str]:
        match = _KEY.fullmatch(key)
        if match is None:
            raise ResearchArtifactStoreUnavailable
        root = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _safe_directory(root)
            research = self._open_directory(root, "research", create)
            try:
                parent = self._open_directory(research, match.group(1), create)
            finally:
                os.close(research)
            return parent, "result.json"
        finally:
            os.close(root)

    @staticmethod
    def _open_directory(parent: int, name: str, create: bool) -> int:
        try:
            descriptor = os.open(
                name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
            )
        except FileNotFoundError:
            if not create:
                raise ResearchArtifactStoreUnavailable from None
            try:
                os.mkdir(name, 0o700, dir_fd=parent)
            except FileExistsError:
                pass
            descriptor = os.open(
                name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent
            )
        _safe_directory(descriptor)
        return descriptor

    @staticmethod
    def _read_file(parent: int, name: str) -> bytes | None:
        try:
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        except FileNotFoundError:
            return None
        try:
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISREG(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or metadata.st_nlink != 1
                or stat.S_IMODE(metadata.st_mode) != 0o600
            ):
                raise ResearchArtifactStoreUnavailable
            chunks = []
            while True:
                chunk = os.read(descriptor, 64 * 1024)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        finally:
            os.close(descriptor)
