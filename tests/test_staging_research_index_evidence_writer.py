from datetime import UTC, datetime
import os

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
)
from liquent_platform.application.staging_research_index_evidence_codec import (
    decode_staging_research_index_evidence,
)
from liquent_platform.application.staging_research_index_request_plan import (
    StagingResearchIndexRequestPhase,
)
from liquent_platform.application.staging_research_index_response_classifier import (
    StagingResearchIndexResponseClassification,
)
from liquent_platform.application.staging_research_index_stage_handoff import (
    StagingResearchIndexStageHandoff,
)
from liquent_platform.application.staging_research_index_staged_acquisition import (
    StagingResearchIndexAcquisitionStage,
)
from liquent_platform.transport.staging_research_index_evidence_writer import (
    StagingResearchIndexEvidenceStorageUnavailable,
    write_staging_research_index_evidence,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "5" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 16, tzinfo=UTC),
)


def _item(check, phase):
    return StagingResearchIndexResponseClassification(
        check, phase, StagingResearchIndexCheckOutcome.PASSED
    )


def _handoffs():
    baseline = tuple(
        _item(check, StagingResearchIndexRequestPhase.SINGLE)
        for check in StagingResearchIndexCheck
        if check not in {
            StagingResearchIndexCheck.REVOCATION_FRESH,
            StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
        }
    ) + (_item(
        StagingResearchIndexCheck.REVOCATION_FRESH,
        StagingResearchIndexRequestPhase.BEFORE_REVOCATION,
    ),)
    return (
        StagingResearchIndexStageHandoff(
            RUN, StagingResearchIndexAcquisitionStage.BASELINE, baseline
        ),
        StagingResearchIndexStageHandoff(
            RUN,
            StagingResearchIndexAcquisitionStage.AFTER_REVOCATION,
            (_item(
                StagingResearchIndexCheck.REVOCATION_FRESH,
                StagingResearchIndexRequestPhase.AFTER_REVOCATION,
            ),),
        ),
        StagingResearchIndexStageHandoff(
            RUN,
            StagingResearchIndexAcquisitionStage.UNAVAILABILITY,
            (_item(
                StagingResearchIndexCheck.UNAVAILABLE_DETAIL_FREE,
                StagingResearchIndexRequestPhase.SINGLE,
            ),),
        ),
    )


def _private_directory(tmp_path):
    directory = tmp_path / "evidence"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    return directory


def test_writer_creates_owner_private_decodable_evidence(tmp_path) -> None:
    target = _private_directory(tmp_path) / "acceptance.json"
    write_staging_research_index_evidence(target, _handoffs())
    assert target.stat().st_mode & 0o777 == 0o600
    assert decode_staging_research_index_evidence(target.read_bytes()) == _handoffs()


def test_writer_never_replaces_existing_target(tmp_path) -> None:
    target = _private_directory(tmp_path) / "acceptance.json"
    target.write_bytes(b"existing")
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        write_staging_research_index_evidence(target, _handoffs())
    assert target.read_bytes() == b"existing"


def test_writer_rejects_non_private_or_symlinked_directory(tmp_path) -> None:
    public = tmp_path / "public"
    public.mkdir(mode=0o755)
    public.chmod(0o755)
    link = tmp_path / "linked"
    link.symlink_to(public, target_is_directory=True)
    for target in (public / "evidence.json", link / "evidence.json"):
        with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
            write_staging_research_index_evidence(target, _handoffs())
        assert not (public / "evidence.json").exists()


def test_writer_rejects_symlink_target_without_touching_destination(tmp_path) -> None:
    directory = _private_directory(tmp_path)
    destination = directory / "destination"
    destination.write_bytes(b"safe")
    target = directory / "acceptance.json"
    target.symlink_to(destination)
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        write_staging_research_index_evidence(target, _handoffs())
    assert destination.read_bytes() == b"safe"


def test_partial_write_failure_removes_incomplete_file(tmp_path, monkeypatch) -> None:
    target = _private_directory(tmp_path) / "acceptance.json"
    real_write = os.write
    calls = 0

    def failing_write(descriptor, content):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError
        return real_write(descriptor, content[:1])

    monkeypatch.setattr(os, "write", failing_write)
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        write_staging_research_index_evidence(target, _handoffs())
    assert not target.exists()


@pytest.mark.parametrize("target", ("relative.json", "/"))
def test_writer_rejects_invalid_paths(target) -> None:
    from pathlib import Path

    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        write_staging_research_index_evidence(Path(target), _handoffs())
