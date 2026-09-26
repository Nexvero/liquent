from datetime import UTC, datetime
import os

import pytest

from liquent_platform.application.staging_research_index_acceptance import (
    StagingResearchIndexAcceptanceRun,
    StagingResearchIndexCheck,
    StagingResearchIndexCheckOutcome,
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
from liquent_platform.transport.staging_research_index_evidence_reader import (
    read_staging_research_index_evidence,
)
from liquent_platform.transport.staging_research_index_evidence_writer import (
    StagingResearchIndexEvidenceStorageUnavailable,
    write_staging_research_index_evidence,
)


RUN = StagingResearchIndexAcceptanceRun(
    "sha256:" + "6" * 64,
    "https://staging.liquent.ai",
    datetime(2026, 9, 15, 17, tzinfo=UTC),
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


def _written(tmp_path):
    directory = tmp_path / "evidence"
    directory.mkdir(mode=0o700)
    directory.chmod(0o700)
    target = directory / "acceptance.json"
    write_staging_research_index_evidence(target, _handoffs())
    return directory, target


def test_reader_returns_exact_canonical_handoffs(tmp_path) -> None:
    _, target = _written(tmp_path)
    assert read_staging_research_index_evidence(target) == _handoffs()


@pytest.mark.parametrize("mode", (0o640, 0o400, 0o666))
def test_reader_rejects_non_private_file_modes(tmp_path, mode) -> None:
    _, target = _written(tmp_path)
    target.chmod(mode)
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        read_staging_research_index_evidence(target)


def test_reader_rejects_non_private_or_symlinked_parent(tmp_path) -> None:
    directory, target = _written(tmp_path)
    directory.chmod(0o755)
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        read_staging_research_index_evidence(target)
    directory.chmod(0o700)
    link = tmp_path / "linked"
    link.symlink_to(directory, target_is_directory=True)
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
        read_staging_research_index_evidence(link / target.name)


def test_reader_rejects_symlink_and_hard_link_targets(tmp_path) -> None:
    directory, target = _written(tmp_path)
    symlink = directory / "linked.json"
    symlink.symlink_to(target)
    hardlink = directory / "hard.json"
    os.link(target, hardlink)
    for candidate in (symlink, target, hardlink):
        with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
            read_staging_research_index_evidence(candidate)


def test_reader_rejects_malformed_empty_and_oversized_content(tmp_path) -> None:
    directory, target = _written(tmp_path)
    for content in (b"", b"{}\n", b"x" * 8_193):
        target.unlink()
        target.write_bytes(content)
        target.chmod(0o600)
        with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
            read_staging_research_index_evidence(target)


def test_reader_rejects_directory_target_and_missing_target(tmp_path) -> None:
    directory, target = _written(tmp_path)
    target.unlink()
    for candidate in (directory, target):
        with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable):
            read_staging_research_index_evidence(candidate)


def test_reader_has_detail_free_representation(tmp_path) -> None:
    _, target = _written(tmp_path)
    target.write_bytes(b"secret")
    with pytest.raises(StagingResearchIndexEvidenceStorageUnavailable) as captured:
        read_staging_research_index_evidence(target)
    assert str(captured.value) == "staging_research_index_evidence_storage_unavailable"
    assert captured.value.__cause__ is None
