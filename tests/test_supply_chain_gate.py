from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import re

import pytest

from tools.verify_image_sbom import verify


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "quality.yml"
GRYPE_CONFIG = ROOT / ".grype.yaml"


def _sbom() -> dict[str, object]:
    return {
        "spdxVersion": "SPDX-2.3",
        "SPDXID": "SPDXRef-DOCUMENT",
        "documentNamespace": "https://liquent.ai/sbom/test",
        "packages": [{"name": "liquent", "versionInfo": "0.0.1"}],
    }


def test_valid_liquent_sbom_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "sbom.json"
    path.write_text(json.dumps(_sbom()), encoding="utf-8")
    assert re.fullmatch(r"[0-9a-f]{64}", verify(path))


@pytest.mark.parametrize("mutation", ["empty", "identity", "namespace", "secret"])
def test_incomplete_or_sensitive_sbom_is_rejected(tmp_path: Path, mutation: str) -> None:
    document = _sbom()
    if mutation == "empty":
        document["packages"] = []
    elif mutation == "identity":
        document["packages"] = [{"name": "something-else"}]
    elif mutation == "namespace":
        document["documentNamespace"] = ""
    else:
        document["files"] = [{"fileName": "/operations/secrets/token"}]
    path = tmp_path / "sbom.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SystemExit, match="SBOM verification failed"):
        verify(path)


def test_supply_chain_tools_and_versions_are_explicit() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    for term in (
        "syft-version: v1.44.0",
        "grype-version: v0.112.0",
        "severity-cutoff: high",
        "only-fixed: true",
        "config: .grype.yaml",
        "verify_image_sbom.py",
    ):
        assert term in workflow


def test_grype_exception_is_narrow_owned_and_time_bounded() -> None:
    config = GRYPE_CONFIG.read_text(encoding="utf-8")
    assert "exception-owner: Liquent Platform Architecture" in config

    # One block per ignore entry, so package and version are checked per CVE
    # rather than anywhere in the file.
    entries = re.split(r"^\s*- vulnerability:", config, flags=re.MULTILINE)[1:]
    assert len(entries) == 3
    for entry in entries:
        assert re.search(r"^\s+name: python$", entry, flags=re.MULTILINE)
        assert re.search(r"^\s+version: 3\.13\.14$", entry, flags=re.MULTILINE)
    assert {entry.splitlines()[0].strip() for entry in entries} == {
        "CVE-2026-15308",
        "CVE-2026-11940",
        "CVE-2026-11972",
    }

    expiry = date.fromisoformat(
        config.split("exception-expires: ", 1)[1].splitlines()[0].strip()
    )
    assert expiry <= date(2026, 8, 31)
    # Fail closed on and after the expiry date, not only after it.
    assert date.today() < expiry


def test_provenance_is_push_only_and_minimally_permissioned() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    block = workflow.split("  provenance:\n", 1)[1]
    assert "if: github.event_name == 'push'" in block
    # Attestation stays gated on the image *and* on the multi-process proof
    # that LQ-178 requires, so neither may be missing on a push to main.
    assert "needs: [container, postgres-integration]" in block
    assert "id-token: write" in block
    assert "attestations: write" in block
    assert "packages: write" not in workflow
    assert "docker push" not in workflow
