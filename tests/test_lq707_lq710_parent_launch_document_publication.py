import ast
from pathlib import Path
from types import SimpleNamespace

from liquent_platform.application.manifest_handoff_supervisor_parent_launch import (
    PersistentManifestHandoffSupervisorParentLaunchPrefix,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_anchor import (
    ManifestHandoffSupervisorLaunchDocumentDigest,
)
from liquent_platform.identity.manifest_handoff_supervisor_launch_document import (
    ManifestHandoffSupervisorLaunchDocumentConflict,
    PublishedManifestHandoffSupervisorLaunchDocument,
)
from liquent_platform.transport.manifest_handoff_supervisor_launch_document import (
    CanonicalManifestHandoffSupervisorLaunchDocumentCodec,
)
from test_lq612_lq613_supervisor_launch_file import document


ROOT = Path(__file__).parents[1]
PARENT = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_parent_launch.py"
PROCESS = ROOT / "src/liquent_platform/application/manifest_handoff_supervisor_process_composition.py"


class Publisher:
    def __init__(self) -> None:
        self.requests = []

    def publish(self, request):
        self.requests.append(request)
        encoded = request.document
        return PublishedManifestHandoffSupervisorLaunchDocument(
            encoded.document.document_id, encoded.facts
        )


def _prefix(publisher: Publisher):
    dependency = object()
    return PersistentManifestHandoffSupervisorParentLaunchPrefix(
        journal=dependency, runtime_bindings=dependency,
        gate_bindings=dependency, engine=dependency,
        launch_documents=publisher,
        launch_document_codec=CanonicalManifestHandoffSupervisorLaunchDocumentCodec(),
    )


def _command(digest: str):
    value = document()
    return SimpleNamespace(
        launch_document_id=value.document_id,
        launch_document_digest=ManifestHandoffSupervisorLaunchDocumentDigest(digest),
        creation_id=value.creation_id,
        gate_binding=value.gate,
        image_digest=value.image_digest,
        registration=SimpleNamespace(process_request=value.request),
    )


def test_parent_reconstructs_and_publishes_exact_canonical_document() -> None:
    publisher = Publisher()
    codec = CanonicalManifestHandoffSupervisorLaunchDocumentCodec()
    expected = codec.encode(document())
    result = _prefix(publisher)._publish_launch_document(
        _command(expected.facts.sha256)
    )
    assert type(result) is PublishedManifestHandoffSupervisorLaunchDocument
    assert len(publisher.requests) == 1
    assert publisher.requests[0].document == expected


def test_digest_divergence_is_effect_free_conflict() -> None:
    publisher = Publisher()
    result = _prefix(publisher)._publish_launch_document(_command("0" * 64))
    assert type(result) is ManifestHandoffSupervisorLaunchDocumentConflict
    assert publisher.requests == []


def test_publication_precedes_runtime_resolution_and_container_create() -> None:
    tree = ast.parse(PARENT.read_text(encoding="utf-8"))
    parent = next(node for node in tree.body if isinstance(node, ast.ClassDef))
    launch = next(
        node for node in parent.body
        if isinstance(node, ast.FunctionDef) and node.name == "_launch"
    )
    text = ast.unparse(launch)
    publish = text.index("self._publish_launch_document(command)")
    resolve = text.index("self._runtime.resolve_runtime")
    assert publish < resolve
    helper = next(
        node for node in parent.body
        if isinstance(node, ast.FunctionDef) and node.name == "_create_and_bind"
    )
    assert "self._engine.create" in ast.unparse(helper)


def test_process_composes_one_publisher_from_shared_root_resolver_and_identity() -> None:
    source = PROCESS.read_text(encoding="utf-8")
    assert source.count("AtomicLocalManifestHandoffSupervisorLaunchDocuments(") == 1
    block = source.split(
        "launch_documents = AtomicLocalManifestHandoffSupervisorLaunchDocuments(", 1
    )[1].split("client = LocalDockerEngineHttpClient(", 1)[0]
    assert "manifest_handoff_supervisor_control_root" in block
    assert "resolve_directory=directories.resolve_active" in block
    assert "identity_policy=identity" in block


def test_parent_has_no_delete_overwrite_or_child_capability_effect() -> None:
    source = PARENT.read_text(encoding="utf-8")
    for forbidden in (
        "delete(", "remove(", "replace(", "execute_writer",
        "execute_recovery", "SessionPrincipal", "allow",
    ):
        assert forbidden not in source
