"""Owner-private no-replace storage for canonical staging evidence."""

import os
from pathlib import Path
import stat

from liquent_platform.application.staging_research_index_evidence_codec import (
    encode_staging_research_index_evidence,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
)


class StagingResearchIndexEvidenceStorageUnavailable(Exception):
    def __init__(self) -> None:
        super().__init__("staging_research_index_evidence_storage_unavailable")


def write_staging_research_index_evidence(
    path: Path,
    handoffs: tuple[StagingResearchIndexStageHandoff, ...],
) -> None:
    """Create one canonical evidence file without replacement."""

    directory_fd = evidence_fd = None
    created = False
    try:
        if (
            not isinstance(path, Path)
            or not path.is_absolute()
            or path == Path("/")
            or ".." in path.parts
            or path.name in {"", ".", ".."}
        ):
            raise StagingResearchIndexEvidenceStorageUnavailable
        content = encode_staging_research_index_evidence(handoffs)
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
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=directory_fd,
        )
        created = True
        if stat.S_IMODE(os.fstat(evidence_fd).st_mode) != 0o600:
            raise StagingResearchIndexEvidenceStorageUnavailable
        written = 0
        while written < len(content):
            count = os.write(evidence_fd, content[written:])
            if type(count) is not int or count < 1:
                raise StagingResearchIndexEvidenceStorageUnavailable
            written += count
        os.fsync(evidence_fd)
        os.close(evidence_fd)
        evidence_fd = None
        os.fsync(directory_fd)
        created = False
    except StagingResearchIndexEvidenceStorageUnavailable:
        raise
    except Exception:
        raise StagingResearchIndexEvidenceStorageUnavailable from None
    finally:
        if evidence_fd is not None:
            try:
                os.close(evidence_fd)
            except Exception:
                pass
        if directory_fd is not None:
            if created:
                try:
                    os.unlink(path.name, dir_fd=directory_fd)
                    os.fsync(directory_fd)
                except Exception:
                    pass
            try:
                os.close(directory_fd)
            except Exception:
                pass
