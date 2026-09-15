"""Bounded owner-private reader for canonical staging evidence."""

import os
from pathlib import Path
import stat

from liquent_platform.application.staging_research_index_evidence_codec import (
    decode_staging_research_index_evidence,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
)
from liquent_platform.transport.staging_research_index_evidence_writer import (
    StagingResearchIndexEvidenceStorageUnavailable,
)


_MAXIMUM_BYTES = 8_192


def read_staging_research_index_evidence(
    path: Path,
) -> tuple[StagingResearchIndexStageHandoff, ...]:
    """Read one descriptor-stable canonical evidence file."""

    directory_fd = evidence_fd = None
    try:
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or path == Path("/")
            or ".." in path.parts
            or path.name in {"", ".", ".."}
        ):
            raise StagingResearchIndexEvidenceStorageUnavailable
        directory_fd = os.open(
            path.parent,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        directory_facts = os.fstat(directory_fd)
        if (
            not stat.S_ISDIR(directory_facts.st_mode)
            or directory_facts.st_uid != os.geteuid()
            or stat.S_IMODE(directory_facts.st_mode) != 0o700
        ):
            raise StagingResearchIndexEvidenceStorageUnavailable
        evidence_fd = os.open(
            path.name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=directory_fd,
        )
        before = os.fstat(evidence_fd)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or stat.S_IMODE(before.st_mode) != 0o600
            or before.st_nlink != 1
            or before.st_size < 1
            or before.st_size > _MAXIMUM_BYTES
        ):
            raise StagingResearchIndexEvidenceStorageUnavailable
        content = bytearray()
        while len(content) <= _MAXIMUM_BYTES:
            chunk = os.read(evidence_fd, min(4096, _MAXIMUM_BYTES + 1 - len(content)))
            if type(chunk) is not bytes:
                raise StagingResearchIndexEvidenceStorageUnavailable
            if not chunk:
                break
            content.extend(chunk)
        after = os.fstat(evidence_fd)
        identity = ("st_dev", "st_ino", "st_mode", "st_uid", "st_nlink", "st_size")
        if (
            len(content) > _MAXIMUM_BYTES
            or len(content) != before.st_size
            or any(getattr(before, name) != getattr(after, name) for name in identity)
        ):
            raise StagingResearchIndexEvidenceStorageUnavailable
        return decode_staging_research_index_evidence(bytes(content))
    except StagingResearchIndexEvidenceStorageUnavailable:
        raise
    except Exception:
        raise StagingResearchIndexEvidenceStorageUnavailable from None
    finally:
        for descriptor in (evidence_fd, directory_fd):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except Exception:
                    pass
