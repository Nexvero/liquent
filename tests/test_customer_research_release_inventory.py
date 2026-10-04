"""Current migration and new customer-source review coverage, without portal gates."""
from hashlib import sha256
from pathlib import Path

from liquent_platform.persistence.migrations import expected_head
from tools.operational_release_bundle import EXPECTED_MIGRATION_COUNT
from tools.pre_staging_manifest import REVIEW_SECTIONS, build_manifest
from test_operational_release_bundle import _wheel
from tools.operational_release_bundle import _wheel_details


ROOT = Path(__file__).parents[1]


def test_current_customer_revision_inventory_and_fail_closed_release_heads():
    migrations = ROOT / "src/liquent_platform/persistence/alembic/versions"
    assert len(list(migrations.glob("*.py"))) == EXPECTED_MIGRATION_COUNT == 47
    assert expected_head() == "20261004_0047"
    source = (migrations / "20261004_0047_customer_research.py").read_text()
    assert 'down_revision = "20260916_0046"' in source
    for relative in ("tools/operational_release_bundle.py", "tools/local_release_preflight_gates.py"):
        assert 'details["migration_head"] != "20261004_0047"' in (ROOT / relative).read_text()
    roadmap = (ROOT / "docs/technical-status-and-roadmap.md").read_text()
    assert "**47 lineare Migrationen**, Head\n  `20261004_0047`" in roadmap
    # Historical migration introduction is not renamed to today's head.
    assert "ergänzt Migration 20260916_0046 ohne Seed-Daten" in roadmap


def test_synthetic_release_fixture_has_current_head_and_all_predecessors(tmp_path):
    path = tmp_path / "liquent-1.2.3-py3-none-any.whl"
    _wheel(path)
    details = _wheel_details(path.read_bytes())
    assert details["migration_head"] == "20261004_0047"


def test_customer_source_scope_has_complete_digest_bound_review_coverage():
    paths = [
        "src/liquent_platform/application/customer_research.py",
        "src/liquent_platform/persistence/customer_research.py",
        "src/liquent_platform/persistence/alembic/versions/20261004_0047_customer_research.py",
        "src/liquent_platform/transport/http/customer_research.py",
        "src/liquent_platform/transport/http/research_customer_ui.py",
        "docs/research-customer-tests.md", "docs/research-pilot-retirement.md",
        "tests/test_customer_research_release_inventory.py",
    ]

    def scoped_git(argv, root):
        assert root == ROOT
        if tuple(argv) == ("git", "rev-parse", "HEAD"):
            return b"a" * 40
        if tuple(argv) == ("git", "branch", "--show-current"):
            return b"review-scope"
        if tuple(argv) == ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"):
            return b"".join(f"?? {path}\0".encode() for path in paths)
        raise AssertionError(argv)

    # This explicitly scoped test does not bypass the real full-tree release gate.
    manifest = build_manifest(ROOT, command_runner=scoped_git)
    assert manifest["file_count"] == len(paths)
    assert {item["path"] for item in manifest["files"]} == set(paths)
    for item in manifest["files"]:
        assert item["review_sections"]
        assert set(item["review_sections"]) <= set(REVIEW_SECTIONS)
        assert item["sha256"] == sha256((ROOT / item["path"]).read_bytes()).hexdigest()
    assert manifest["deployment_authorized"] is False
