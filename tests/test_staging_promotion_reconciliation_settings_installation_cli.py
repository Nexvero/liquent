from io import StringIO
from pathlib import Path

import pytest

from liquent_platform.transport import (
    staging_research_index_promotion_reconciliation_settings_installation_cli as cli,
)
from liquent_platform.transport.staging_research_index_promotion_reconciliation_settings_installer import (  # noqa: E501
    StagingResearchIndexPromotionReconciliationSettingsInstallationOutcome as Outcome,
)


ARGS = (
    "/run/liquent/source/provider.env",
    "/run/liquent/provider.env",
    "/run/liquent/source/process.env",
    "/run/liquent/process.env",
)


@pytest.mark.parametrize(
    "outcome,token,code,stream",
    [
        (Outcome.INSTALLED, "installed\n", 0, "stdout"),
        (Outcome.PRESENT, "present\n", 3, "stderr"),
    ],
)
def test_known_outcomes_have_fixed_token_stream_and_exit(
    monkeypatch, outcome, token, code, stream
) -> None:
    calls = []
    monkeypatch.setattr(
        cli,
        "install_staging_research_index_promotion_reconciliation_settings",
        lambda *paths: calls.append(paths) or outcome,
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(ARGS, stdout=stdout, stderr=stderr) == code
    assert stdout.getvalue() == (token if stream == "stdout" else "")
    assert stderr.getvalue() == (token if stream == "stderr" else "")
    assert calls == [tuple(Path(value) for value in ARGS)]


def test_technical_failure_is_detail_free_unavailability(monkeypatch) -> None:
    def unavailable(*_paths):
        raise RuntimeError("endpoint and database password detail")

    monkeypatch.setattr(
        cli,
        "install_staging_research_index_promotion_reconciliation_settings",
        unavailable,
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(ARGS, stdout=stdout, stderr=stderr) == 1
    assert stdout.getvalue() == "" and stderr.getvalue() == "unavailable\n"
    assert "password" not in stderr.getvalue()


@pytest.mark.parametrize(
    "argv",
    [
        (),
        ARGS[:3],
        ARGS + ("/extra",),
        ("relative",) + ARGS[1:],
        ("/",) + ARGS[1:],
        ("/run/../secret",) + ARGS[1:],
        [*ARGS],
        (ARGS[0], ARGS[1], ARGS[2], object()),
    ],
)
def test_invalid_invocation_never_calls_installer(monkeypatch, argv) -> None:
    calls = []
    monkeypatch.setattr(
        cli,
        "install_staging_research_index_promotion_reconciliation_settings",
        lambda *paths: calls.append(paths),
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(argv, stdout=stdout, stderr=stderr) == 2
    assert stdout.getvalue() == "" and stderr.getvalue() == "invalid_invocation\n"
    assert calls == []


def test_unknown_outcome_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "install_staging_research_index_promotion_reconciliation_settings",
        lambda *_: object(),
    )
    stdout, stderr = StringIO(), StringIO()
    assert cli.run(ARGS, stdout=stdout, stderr=stderr) == 1
    assert stdout.getvalue() == "" and stderr.getvalue() == "unavailable\n"
