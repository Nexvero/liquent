#!/usr/bin/env python3
"""Build and verify unsigned deterministic operational release candidates."""

from __future__ import annotations

import argparse
import ast
import configparser
import gzip
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn


BUNDLE_FORMAT_VERSION = 1
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
VERSION_RE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
SHA256_RE = re.compile(r"[0-9a-f]{64}")
MIGRATION_RE = re.compile(
    r"liquent_platform/persistence/alembic/versions/[^/]+\.py"
)
OPERATOR_RE = re.compile(r"liquent_platform/operators/[^/]+\.py")
EXPECTED_ENTRY_POINT_COUNT = 71
EXPECTED_OPERATOR_FILE_COUNT = 71
EXPECTED_MIGRATION_COUNT = 42

RUNBOOKS = (
    "initial-identity-and-trust-authority-bootstrap.md",
    "oidc-trust-management.md",
    "oidc-trust-authority-lifecycle.md",
    "oidc-trust-authority-recovery.md",
    "workspace-membership-management.md",
    "workspace-membership-authority-lifecycle.md",
    "workspace-membership-authority-recovery.md",
    "user-lifecycle.md",
    "workspace-lifecycle.md",
    "backup-restore.md",
    "initial-staging-bootstrap.md",
    "release-environment-readiness.md",
    "release-publication-worker.md",
    "research-worker-staging-readiness.md",
    "staging-promotion.md",
    "disposable-postgres-runtime-cleanup.md",
    "disposable-postgres-volume-disposition-deletion.md",
)
CONTRACTS = (
    "lq-177-controlled-production-wiring-resumption.md",
    "lq-197-oidc-process-runtime-contract.md",
    "lq-211-authority-lifecycle-and-recovery-contract.md",
    "lq-219-persistent-user-workspace-lifecycle-contract.md",
    "lq-228-controlled-lifecycle-revision-observability-contract.md",
    "lq-231-postgresql-verification-and-readiness-decision.md",
    "lq-232-controlled-release-handoff-audit.md",
    "lq-234-release-artifact-preflight.md",
    "lq-235-versioned-operational-release-bundle-contract.md",
    "lq-237-detached-release-signature-and-promotion-contract.md",
    "lq-270-controlled-offline-publication-worker-contract.md",
    "lq-285-release-publication-end-to-end-readiness-and-runbook-handoff.md",
    "lq-286-environment-provider-and-deployment-release-contract.md",
    "lq-289-persistent-research-worker-foundation-contract.md",
    "lq-303-research-worker-staging-readiness-audit.md",
    "lq-304-offline-research-worker-staging-evidence-verifier.md",
    "lq-305-controlled-research-worker-staging-executor-contract.md",
    "lq-313-controlled-runtime-inspection-contract.md",
    "lq-316-controlled-artifact-capability-probe-contract.md",
    "lq-319-controlled-artifact-probe-recovery-contract.md",
    "lq-326-artifact-capability-recovery-end-to-end-audit.md",
    "lq-327-disposable-postgresql-and-current-rollback-evidence-contract.md",
    "lq-334-disposable-postgresql-recovery-disposition-contract.md",
    "lq-336-disposable-postgresql-cleanup-authorization-preflight-contract.md",
    "lq-338-runtime-only-disposable-postgresql-cleanup-contract.md",
    "lq-377-bounded-generation-lineage-contract.md",
    "lq-385-runtime-cleanup-release-and-operational-readiness-audit.md",
    "lq-386-owner-controlled-runtime-cleanup-operational-handoff-contract.md",
    "lq-388-postgresql-volume-disposition-contract.md",
    "lq-391-owner-only-postgresql-volume-deletion-authorization-preflight-contract.md",
    "lq-393-owner-controlled-evidence-first-postgresql-volume-deletion-contract.md",
    "lq-408-owner-controlled-postgresql-volume-disposition-deletion-operational-handoff-contract.md",
    "lq-410-postgresql-volume-disposition-deletion-operational-release-readiness-reaudit.md",
    "lq-411-cumulative-worktree-integration-release-handoff-audit.md",
    "lq-412-consolidated-roadmap-status-gate-consistency.md",
    "lq-491-retired-supervisor-control-directory-retention-and-cleanup-contract.md",
    "lq-518-owner-controlled-single-supervisor-control-directory-cleanup-operator-contract.md",
    "lq-585-owner-controlled-supervisor-control-directory-retirement-operator-contract.md",
    "lq-522-supervisor-control-directory-cleanup-end-to-end-readiness-audit.md",
    "lq-537-owner-controlled-supervisor-cleanup-retention-policy-operator-contract.md",
    "lq-524-owner-controlled-supervisor-cleanup-authority-and-source-revision-operator-contract.md",
    "lq-525-owner-controlled-supervisor-cleanup-authority-set-operators.md",
    "lq-526-owner-controlled-supervisor-cleanup-source-revision-operator.md",
    "lq-679-fixed-child-process-composition-contract.md",
    "lq-682-fixed-child-entrypoint-completion-audit.md",
)
EXAMPLE = "runtime.env.example"
EVIDENCE_NAME = "verification.json"
MANIFEST_NAME = "manifest.json"
CHECKSUM_NAME = "SHA256SUMS"

EVIDENCE_KEYS = {
    "schema_version",
    "source_commit",
    "test_command",
    "total_passed",
    "postgres_passed",
    "warnings",
    "versions",
    "wheel_import_check",
    "migration_check",
    "secret_scan",
    "diff_check",
}
VERSION_KEYS = {
    "python", "pytest", "postgresql", "sqlalchemy", "psycopg"
}
MANIFEST_KEYS = {
    "bundle_format_version",
    "product_name",
    "package_name",
    "package_version",
    "source_commit",
    "source_tree_clean",
    "source_date_epoch",
    "python_requires",
    "migration_head",
    "wheel",
    "console_entry_points",
    "runbooks",
    "contracts",
    "examples",
    "verification",
    "signature_policy",
}
SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"ghp_[A-Za-z0-9]{30,}"),
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"/Users/[^/\s]+/"),
    re.compile(rb"/tmp/liquent-[^\s]+"),
)


class BundleRejected(Exception):
    """One detail-limited release-candidate validation failure."""


def _reject() -> NoReturn:
    raise BundleRejected("operational release bundle rejected")


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _entry(path: str, value: bytes, **extra: object) -> dict[str, object]:
    return {
        "path": path,
        "sha256": _sha256(value),
        "size": len(value),
        **extra,
    }


def _read_regular(path: Path) -> bytes:
    try:
        if path.is_symlink() or not path.is_file():
            _reject()
        return path.read_bytes()
    except BundleRejected:
        raise
    except OSError:
        _reject()


def _json_object(value: bytes) -> dict[str, Any]:
    try:
        result = json.loads(value)
    except (UnicodeError, json.JSONDecodeError):
        _reject()
    if not isinstance(result, dict):
        _reject()
    return result


def _validate_evidence(value: bytes, source_commit: str) -> dict[str, Any]:
    evidence = _json_object(value)
    if set(evidence) != EVIDENCE_KEYS or evidence.get("schema_version") != 1:
        _reject()
    if evidence.get("source_commit") != source_commit:
        _reject()
    for name in ("total_passed", "postgres_passed"):
        count = evidence.get(name)
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            _reject()
    warnings = evidence.get("warnings")
    if isinstance(warnings, bool) or not isinstance(warnings, int) or warnings < 0:
        _reject()
    test_command = evidence.get("test_command")
    if not isinstance(test_command, str) or not test_command.strip():
        _reject()
    if "://" in test_command or "LIQUENT_TEST_DATABASE_URL=" in test_command:
        _reject()
    versions = evidence.get("versions")
    if not isinstance(versions, dict) or set(versions) != VERSION_KEYS:
        _reject()
    if any(not isinstance(item, str) or not item for item in versions.values()):
        _reject()
    for name in (
        "wheel_import_check", "migration_check", "secret_scan", "diff_check"
    ):
        if evidence.get(name) != "passed":
            _reject()
    return evidence


def _literal_assignment(source: bytes, name: str) -> str | None:
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        _reject()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
            value = node.value
        else:
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            if isinstance(value, ast.Constant) and (
                isinstance(value.value, str) or value.value is None
            ):
                return value.value
            _reject()
    _reject()


def _wheel_details(value: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(value)) as wheel:
            names = wheel.namelist()
            metadata_names = [
                name for name in names if name.endswith(".dist-info/METADATA")
            ]
            entry_names = [
                name for name in names if name.endswith(".dist-info/entry_points.txt")
            ]
            if len(metadata_names) != 1 or len(entry_names) != 1:
                _reject()
            metadata = BytesParser().parsebytes(wheel.read(metadata_names[0]))
            package_name = metadata.get("Name")
            package_version = metadata.get("Version")
            python_requires = metadata.get("Requires-Python")
            if (
                package_name != "liquent"
                or not isinstance(package_version, str)
                or not VERSION_RE.fullmatch(package_version)
                or not isinstance(python_requires, str)
                or not python_requires
            ):
                _reject()

            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read_string(wheel.read(entry_names[0]).decode("utf-8"))
            if set(parser.sections()) != {"console_scripts"}:
                _reject()
            entry_points = [
                {"name": name, "target": target}
                for name, target in sorted(parser.items("console_scripts"))
            ]
            if len(entry_points) != EXPECTED_ENTRY_POINT_COUNT:
                _reject()

            migrations = sorted(name for name in names if MIGRATION_RE.fullmatch(name))
            if len(migrations) != EXPECTED_MIGRATION_COUNT:
                _reject()
            revisions: dict[str, str | None] = {}
            for name in migrations:
                revision = _literal_assignment(wheel.read(name), "revision")
                down_revision = _literal_assignment(wheel.read(name), "down_revision")
                if revision is None or revision in revisions:
                    _reject()
                revisions[revision] = down_revision
            referenced = {value for value in revisions.values() if value is not None}
            heads = set(revisions) - referenced
            roots = [key for key, value in revisions.items() if value is None]
            if len(heads) != 1 or len(roots) != 1:
                _reject()
            head = next(iter(heads))
            visited: set[str] = set()
            current: str | None = head
            while current is not None:
                if current in visited or current not in revisions:
                    _reject()
                visited.add(current)
                current = revisions[current]
            if len(visited) != len(revisions):
                _reject()

            operators = sorted(name for name in names if OPERATOR_RE.fullmatch(name))
            if len(operators) != EXPECTED_OPERATOR_FILE_COUNT:
                _reject()
    except BundleRejected:
        raise
    except (
        OSError,
        KeyError,
        UnicodeError,
        configparser.Error,
        zipfile.BadZipFile,
    ):
        _reject()
    return {
        "package_name": package_name,
        "package_version": package_version,
        "python_requires": python_requires,
        "entry_points": entry_points,
        "migration_count": len(migrations),
        "migration_head": head,
        "operator_module_count": len(operators),
    }


def _scan_payload(path: str, value: bytes) -> None:
    if "\x00" in path or path.startswith("/") or ".." in PurePosixPath(path).parts:
        _reject()
    for pattern in SECRET_PATTERNS:
        if pattern.search(value) or pattern.search(path.encode("utf-8")):
            _reject()


def _clean_git_source(source_root: Path, source_commit: str) -> None:
    try:
        current = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source_root,
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=source_root, check=True, capture_output=True, text=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        _reject()
    if current != source_commit or status:
        _reject()


def _safe_source_date_epoch(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _reject()
    return value


def _copy_payload(source_root: Path, wheel_path: Path, evidence_path: Path) -> dict[str, bytes]:
    payload: dict[str, bytes] = {}
    payload[f"artifacts/{wheel_path.name}"] = _read_regular(wheel_path)
    for name in RUNBOOKS:
        payload[f"runbooks/{name}"] = _read_regular(
            source_root / "operations" / "runbooks" / name
        )
    for name in CONTRACTS:
        payload[f"contracts/{name}"] = _read_regular(source_root / "docs" / name)
    payload[f"examples/{EXAMPLE}"] = _read_regular(
        source_root / "operations" / "compose" / EXAMPLE
    )
    payload[f"evidence/{EVIDENCE_NAME}"] = _read_regular(evidence_path)
    for path, value in payload.items():
        _scan_payload(path, value)
    return payload


def _manifest(
    payload: dict[str, bytes], source_commit: str, source_date_epoch: int
) -> dict[str, object]:
    wheel_paths = [path for path in payload if path.startswith("artifacts/")]
    if len(wheel_paths) != 1:
        _reject()
    wheel_path = wheel_paths[0]
    details = _wheel_details(payload[wheel_path])
    expected_wheel_name = (
        f"liquent-{details['package_version']}-py3-none-any.whl"
    )
    if Path(wheel_path).name != expected_wheel_name:
        _reject()
    evidence_path = f"evidence/{EVIDENCE_NAME}"
    _validate_evidence(payload[evidence_path], source_commit)
    if details["migration_head"] != "20260826_0042":
        _reject()

    def entries(prefix: str, **extra: object) -> list[dict[str, object]]:
        return [
            _entry(path, payload[path], **extra)
            for path in sorted(payload)
            if path.startswith(prefix)
        ]

    return {
        "bundle_format_version": BUNDLE_FORMAT_VERSION,
        "product_name": "Liquent",
        "package_name": details["package_name"],
        "package_version": details["package_version"],
        "source_commit": source_commit,
        "source_tree_clean": True,
        "source_date_epoch": source_date_epoch,
        "python_requires": details["python_requires"],
        "migration_head": details["migration_head"],
        "wheel": _entry(
            wheel_path,
            payload[wheel_path],
            filename=Path(wheel_path).name,
            package_version=details["package_version"],
            migration_count=details["migration_count"],
            migration_head=details["migration_head"],
            operator_module_count=details["operator_module_count"],
        ),
        "console_entry_points": details["entry_points"],
        "runbooks": entries("runbooks/"),
        "contracts": entries("contracts/", classification="required"),
        "examples": entries("examples/"),
        "verification": _entry(evidence_path, payload[evidence_path]),
        "signature_policy": {
            "required_for_promotion": True,
            "status": "unsigned_candidate",
            "detached_over": CHECKSUM_NAME,
        },
    }


def _write_archive(
    output_path: Path,
    root_name: str,
    payload: dict[str, bytes],
    source_date_epoch: int,
) -> None:
    if output_path.exists() or output_path.is_symlink():
        _reject()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.tmp")
    if temporary.exists() or temporary.is_symlink():
        _reject()
    directories = {root_name}
    for path in payload:
        current = PurePosixPath(root_name, path).parent
        while str(current) != ".":
            directories.add(str(current))
            if str(current) == root_name:
                break
            current = current.parent
    try:
        with temporary.open("xb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=source_date_epoch) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                    for directory in sorted(directories):
                        info = tarfile.TarInfo(directory + "/")
                        info.type = tarfile.DIRTYPE
                        info.mode = 0o755
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mtime = source_date_epoch
                        archive.addfile(info)
                    for path in sorted(payload):
                        value = payload[path]
                        info = tarfile.TarInfo(f"{root_name}/{path}")
                        info.size = len(value)
                        info.mode = 0o644
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mtime = source_date_epoch
                        archive.addfile(info, io.BytesIO(value))
        temporary.replace(output_path)
    except Exception as error:
        try:
            temporary.unlink()
        except OSError:
            pass
        if isinstance(error, BundleRejected):
            raise
        _reject()


def build_bundle(
    *,
    source_root: Path,
    wheel_path: Path,
    evidence_path: Path,
    output_directory: Path,
    source_commit: str,
    source_date_epoch: int,
    enforce_clean_source: bool = True,
) -> Path:
    """Build one unsigned candidate without publishing or signing it."""

    if not COMMIT_RE.fullmatch(source_commit):
        _reject()
    epoch = _safe_source_date_epoch(source_date_epoch)
    if enforce_clean_source:
        _clean_git_source(source_root, source_commit)
    payload = _copy_payload(source_root, wheel_path, evidence_path)
    manifest = _manifest(payload, source_commit, epoch)
    package_version = manifest["package_version"]
    root_name = f"liquent-operations-{package_version}-{source_commit[:12]}"
    payload[MANIFEST_NAME] = _canonical_json(manifest)
    checksums = "".join(
        f"{_sha256(payload[path])}  {path}\n" for path in sorted(payload)
    ).encode("ascii")
    payload[CHECKSUM_NAME] = checksums
    output_path = output_directory / f"{root_name}.tar.gz"
    _write_archive(output_path, root_name, payload, epoch)
    return output_path


def _safe_member(member: tarfile.TarInfo) -> tuple[str, str]:
    if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
        _reject()
    pure = PurePosixPath(member.name)
    if member.name.startswith("/") or ".." in pure.parts or not pure.parts:
        _reject()
    if str(pure) != member.name.rstrip("/"):
        _reject()
    root = pure.parts[0]
    relative = PurePosixPath(*pure.parts[1:]).as_posix()
    return root, relative


def verify_bundle(path: Path) -> dict[str, object]:
    """Verify one unsigned candidate in memory without extracting it."""

    archive_value = _read_regular(path)
    files: dict[str, bytes] = {}
    directories: set[str] = set()
    root_name: str | None = None
    mtimes: set[int | float] = set()
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_value), mode="r:gz") as archive:
            for member in archive.getmembers():
                root, relative = _safe_member(member)
                if root_name is None:
                    root_name = root
                elif root != root_name:
                    _reject()
                mtimes.add(member.mtime)
                if member.isdir():
                    if member.mode != 0o755:
                        _reject()
                    directories.add(relative)
                    continue
                if member.mode != 0o644 or not relative or relative in files:
                    _reject()
                extracted = archive.extractfile(member)
                if extracted is None:
                    _reject()
                files[relative] = extracted.read()
    except BundleRejected:
        raise
    except (OSError, tarfile.TarError):
        _reject()
    if root_name is None or len(mtimes) != 1:
        _reject()
    if set(files) < {MANIFEST_NAME, CHECKSUM_NAME}:
        _reject()
    manifest = _json_object(files[MANIFEST_NAME])
    if set(manifest) != MANIFEST_KEYS:
        _reject()
    if files[MANIFEST_NAME] != _canonical_json(manifest):
        _reject()
    if manifest.get("bundle_format_version") != BUNDLE_FORMAT_VERSION:
        _reject()
    if manifest.get("product_name") != "Liquent":
        _reject()
    if manifest.get("source_tree_clean") is not True:
        _reject()
    epoch = manifest.get("source_date_epoch")
    if _safe_source_date_epoch(epoch) not in mtimes:
        _reject()
    commit = manifest.get("source_commit")
    if not isinstance(commit, str) or not COMMIT_RE.fullmatch(commit):
        _reject()
    expected_root = (
        f"liquent-operations-{manifest.get('package_version')}-{commit[:12]}"
    )
    if root_name != expected_root or path.name != expected_root + ".tar.gz":
        _reject()

    checksum_lines = files[CHECKSUM_NAME].decode("ascii").splitlines()
    expected_paths = sorted(set(files) - {CHECKSUM_NAME})
    if len(checksum_lines) != len(expected_paths):
        _reject()
    parsed: dict[str, str] = {}
    listed_paths: list[str] = []
    for line in checksum_lines:
        if len(line) < 67 or line[64:66] != "  ":
            _reject()
        digest, item = line[:64], line[66:]
        if not SHA256_RE.fullmatch(digest) or item in parsed:
            _reject()
        parsed[item] = digest
        listed_paths.append(item)
    if listed_paths != expected_paths:
        _reject()
    for item, digest in parsed.items():
        if _sha256(files[item]) != digest:
            _reject()

    wheel = manifest.get("wheel")
    if not isinstance(wheel, dict) or set(wheel) != {
        "path", "sha256", "size", "filename", "package_version",
        "migration_count", "migration_head", "operator_module_count",
    }:
        _reject()
    wheel_path = wheel.get("path")
    if not isinstance(wheel_path, str) or wheel_path not in files:
        _reject()
    details = _wheel_details(files[wheel_path])
    if (
        wheel.get("sha256") != _sha256(files[wheel_path])
        or wheel.get("size") != len(files[wheel_path])
        or wheel.get("filename") != Path(wheel_path).name
        or wheel.get("package_version") != details["package_version"]
        or wheel.get("migration_count") != details["migration_count"]
        or wheel.get("migration_head") != details["migration_head"]
        or wheel.get("operator_module_count") != details["operator_module_count"]
        or manifest.get("console_entry_points") != details["entry_points"]
        or manifest.get("migration_head") != details["migration_head"]
        or manifest.get("package_name") != details["package_name"]
        or manifest.get("package_version") != details["package_version"]
        or manifest.get("python_requires") != details["python_requires"]
    ):
        _reject()

    inventories = {
        "runbooks": set(RUNBOOKS),
        "contracts": set(CONTRACTS),
        "examples": {EXAMPLE},
    }
    for key, names in inventories.items():
        entries = manifest.get(key)
        if not isinstance(entries, list) or len(entries) != len(names):
            _reject()
        entry_paths = [
            entry.get("path") for entry in entries if isinstance(entry, dict)
        ]
        if len(entry_paths) != len(entries) or entry_paths != sorted(entry_paths):
            _reject()
        prefix = key + "/"
        seen: set[str] = set()
        for entry in entries:
            expected_keys = {"path", "sha256", "size"}
            if key == "contracts":
                expected_keys.add("classification")
            if not isinstance(entry, dict) or set(entry) != expected_keys:
                _reject()
            item = entry.get("path")
            if not isinstance(item, str) or item not in files or not item.startswith(prefix):
                _reject()
            if Path(item).name not in names or item in seen:
                _reject()
            if entry.get("sha256") != _sha256(files[item]) or entry.get("size") != len(files[item]):
                _reject()
            if key == "contracts" and entry.get("classification") != "required":
                _reject()
            seen.add(item)
        if {Path(item).name for item in seen} != names:
            _reject()

    verification = manifest.get("verification")
    evidence_path = f"evidence/{EVIDENCE_NAME}"
    if not isinstance(verification, dict) or set(verification) != {
        "path", "sha256", "size"
    }:
        _reject()
    if verification.get("path") != evidence_path or evidence_path not in files:
        _reject()
    if (
        verification.get("sha256") != _sha256(files[evidence_path])
        or verification.get("size") != len(files[evidence_path])
    ):
        _reject()
    _validate_evidence(files[evidence_path], commit)

    policy = manifest.get("signature_policy")
    if policy != {
        "required_for_promotion": True,
        "status": "unsigned_candidate",
        "detached_over": CHECKSUM_NAME,
    }:
        _reject()
    expected_file_set = {
        MANIFEST_NAME,
        CHECKSUM_NAME,
        wheel_path,
        evidence_path,
        f"examples/{EXAMPLE}",
        *(f"runbooks/{name}" for name in RUNBOOKS),
        *(f"contracts/{name}" for name in CONTRACTS),
    }
    if set(files) != expected_file_set:
        _reject()
    expected_directories = {
        ".",
        "artifacts",
        "runbooks",
        "contracts",
        "evidence",
        "examples",
    }
    if directories != expected_directories:
        _reject()
    return {
        "bundle_format_version": BUNDLE_FORMAT_VERSION,
        "source_commit": commit,
        "package_version": details["package_version"],
        "migration_head": details["migration_head"],
        "integrity": "verified",
        "signature": "not_verified",
        "promotable": False,
    }


def _build_command(args: argparse.Namespace) -> int:
    path = build_bundle(
        source_root=args.source_root,
        wheel_path=args.wheel,
        evidence_path=args.evidence,
        output_directory=args.output_directory,
        source_commit=args.source_commit,
        source_date_epoch=args.source_date_epoch,
    )
    print(json.dumps({"outcome": "candidate_built", "path": path.name}, sort_keys=True))
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    print(json.dumps(verify_bundle(args.bundle), sort_keys=True))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="operational-release-bundle")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--source-root", type=Path, required=True)
    build.add_argument("--wheel", type=Path, required=True)
    build.add_argument("--evidence", type=Path, required=True)
    build.add_argument("--output-directory", type=Path, required=True)
    build.add_argument("--source-commit", required=True)
    build.add_argument("--source-date-epoch", type=int, required=True)
    build.set_defaults(operation=_build_command)
    verify = commands.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    verify.set_defaults(operation=_verify_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.operation(args)
    except BundleRejected:
        print(json.dumps({"error": "operational_release_bundle_rejected"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
