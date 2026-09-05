import hashlib
import os
from pathlib import Path

import pytest

from liquent_platform.application.ports import ArtifactReference
from liquent_platform.persistence.research_artifacts import (
    LocalImmutableResearchArtifactStore,
    ResearchArtifactStoreUnavailable,
)


KEY = "research/" + "a" * 64 + "/result.json"
CONTENT = b'{"result":"controlled"}'


def _root(tmp_path: Path) -> Path:
    root = tmp_path / "artifacts"
    root.mkdir(mode=0o700)
    return root


def test_put_is_atomic_immutable_and_exact_retry_is_idempotent(tmp_path: Path):
    root = _root(tmp_path)
    store = LocalImmutableResearchArtifactStore(root)
    first = store.put(key=KEY, content=CONTENT, media_type="application/json")
    second = store.put(key=KEY, content=CONTENT, media_type="application/json")
    assert first == second == ArtifactReference(
        KEY, hashlib.sha256(CONTENT).hexdigest(), "application/json", len(CONTENT)
    )
    target = root / KEY
    assert target.read_bytes() == CONTENT
    assert target.stat().st_mode & 0o777 == 0o600
    assert list(target.parent.glob(".result-*.tmp")) == []


def test_divergent_retry_never_overwrites_existing_bytes(tmp_path: Path):
    root = _root(tmp_path)
    store = LocalImmutableResearchArtifactStore(root)
    store.put(key=KEY, content=CONTENT, media_type="application/json")
    with pytest.raises(ResearchArtifactStoreUnavailable):
        store.put(key=KEY, content=b"different", media_type="application/json")
    assert (root / KEY).read_bytes() == CONTENT


@pytest.mark.parametrize("key", [
    "../result.json", "/research/" + "a" * 64 + "/result.json",
    "research/not-a-hash/result.json", "research/" + "a" * 64 + "/other.json",
])
def test_key_grammar_rejects_traversal_absolute_and_free_names(tmp_path: Path, key: str):
    store = LocalImmutableResearchArtifactStore(_root(tmp_path))
    with pytest.raises(ResearchArtifactStoreUnavailable):
        store.put(key=key, content=CONTENT, media_type="application/json")


def test_symlinked_directory_is_rejected_without_touching_target(tmp_path: Path):
    root = _root(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "research").symlink_to(outside, target_is_directory=True)
    store = LocalImmutableResearchArtifactStore(root)
    with pytest.raises(ResearchArtifactStoreUnavailable):
        store.put(key=KEY, content=CONTENT, media_type="application/json")
    assert list(outside.iterdir()) == []


def test_get_verifies_reference_hash_size_mode_and_content(tmp_path: Path):
    root = _root(tmp_path)
    store = LocalImmutableResearchArtifactStore(root)
    reference = store.put(key=KEY, content=CONTENT, media_type="application/json")
    assert store.get(reference) == CONTENT
    (root / KEY).write_bytes(b"tampered")
    os.chmod(root / KEY, 0o600)
    with pytest.raises(ResearchArtifactStoreUnavailable) as caught:
        store.get(reference)
    assert str(caught.value) == "research_artifact_store_unavailable"
    assert caught.value.__cause__ is None


def test_root_must_be_absolute_existing_owner_controlled_directory(tmp_path: Path):
    with pytest.raises(ValueError):
        LocalImmutableResearchArtifactStore(Path("relative"))
    loose = tmp_path / "loose"
    loose.mkdir(mode=0o777)
    os.chmod(loose, 0o777)
    with pytest.raises(ResearchArtifactStoreUnavailable):
        LocalImmutableResearchArtifactStore(loose)


def test_repr_discloses_no_root(tmp_path: Path):
    root = _root(tmp_path)
    assert repr(LocalImmutableResearchArtifactStore(root)) == (
        "LocalImmutableResearchArtifactStore()"
    )
    assert str(root) not in repr(LocalImmutableResearchArtifactStore(root))
