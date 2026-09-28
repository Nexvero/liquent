"""Complete local composition for one controlled publication worker."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from sqlalchemy import Engine

from liquent_platform.application.process_release_publication_work import (
    ProcessReleasePublicationWork,
)
from liquent_platform.identity.ports import ReleasePublicationArtifactSource
from liquent_platform.identity.release_authority import ReleasePromotionVerifierId
from liquent_platform.identity.release_publication import (
    ReleasePublicationAttemptId,
    ReleasePublicationExecutorId,
    ReleasePublicationProviderReceiptId,
    ReleasePublicationReassessmentId,
    ReleasePublicationRecoveryId,
)
from liquent_platform.persistence.release_publication_artifacts import (
    DatabaseReleasePublicationArtifactIntegrityCheck,
)
from liquent_platform.persistence.release_publication_attempt import (
    DatabaseReleasePublicationAttemptPreflight,
)
from liquent_platform.persistence.release_publication_create import (
    DatabaseReleasePublicationImmutableCreate,
)
from liquent_platform.persistence.release_publication_finalize import (
    DatabaseReleasePublicationReconciliationFinalizer,
)
from liquent_platform.persistence.release_publication_reconciliation import (
    DatabaseReleasePublicationUnknownOutcomeReconciliation,
)
from liquent_platform.persistence.release_publication_recovery import (
    DatabaseReleasePublicationRecoveryFinalizer,
)
from liquent_platform.persistence.release_publication_retry import (
    DatabaseReleasePublicationRetryAttemptPreflight,
)
from liquent_platform.persistence.release_publication_retry_create import (
    DatabaseReleasePublicationRetryImmutableCreate,
)
from liquent_platform.persistence.release_publication_target import (
    DatabaseReleasePublicationTargetInspection,
)
from liquent_platform.persistence.release_publication_work import (
    DatabaseReleasePublicationCurrentOutcomeFinalizer,
    DatabaseReleasePublicationWorkStateLookup,
)
from liquent_platform.persistence.release_registry_projection import (
    DatabaseCurrentReleaseAuthorityRegistryProjection,
)
from liquent_platform.transport.package_index_composition import (
    PackageIndexPublicationComposition,
)


class ReleasePublicationWorkerCompositionUnavailable(Exception):
    code = "release_publication_worker_composition_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)


class ReleasePublicationWorkerComposition:
    """Own one database engine and provider composition for one worker."""

    __slots__ = ("_engine", "_provider", "worker")

    def __init__(
        self,
        engine: Engine,
        provider: PackageIndexPublicationComposition,
        worker: ProcessReleasePublicationWork,
    ) -> None:
        self._engine: Engine | None = engine
        self._provider: PackageIndexPublicationComposition | None = provider
        self.worker = worker

    def __repr__(self) -> str:
        return "ReleasePublicationWorkerComposition()"

    def __enter__(self) -> ReleasePublicationWorkerComposition:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        provider, self._provider = self._provider, None
        engine, self._engine = self._engine, None
        failed = False
        if provider is not None:
            try:
                provider.close()
            except Exception:
                failed = True
        if engine is not None:
            try:
                engine.dispose()
            except Exception:
                failed = True
        if failed:
            raise ReleasePublicationWorkerCompositionUnavailable


def compose_release_publication_worker(
    *,
    engine: Engine,
    provider: PackageIndexPublicationComposition,
    artifact_source: ReleasePublicationArtifactSource,
    executor_id: ReleasePublicationExecutorId,
    promotion_verifier_id: ReleasePromotionVerifierId,
    generate_attempt_id: Callable[[], ReleasePublicationAttemptId],
    generate_receipt_id: Callable[[], ReleasePublicationProviderReceiptId],
    generate_recovery_id: Callable[[], ReleasePublicationRecoveryId],
    generate_reassessment_id: Callable[[], ReleasePublicationReassessmentId],
    clock: Callable[[], datetime] | None = None,
    ssh_keygen: str = "ssh-keygen",
) -> ReleasePublicationWorkerComposition:
    """Take ownership and compose every dependency without operational I/O."""

    try:
        if (
            not isinstance(engine, Engine)
            or type(provider) is not PackageIndexPublicationComposition
            or type(executor_id) is not ReleasePublicationExecutorId
            or type(promotion_verifier_id) is not ReleasePromotionVerifierId
            or type(ssh_keygen) is not str
            or not ssh_keygen
        ):
            raise ReleasePublicationWorkerCompositionUnavailable
        projection = DatabaseCurrentReleaseAuthorityRegistryProjection(
            engine, verification_identity=promotion_verifier_id
        )
        integrity = DatabaseReleasePublicationArtifactIntegrityCheck(
            engine,
            artifact_source=artifact_source,
            registry_projection=projection,
            clock=clock,
            ssh_keygen=ssh_keygen,
        )
        adapter = provider.publication
        inspection = DatabaseReleasePublicationTargetInspection(
            engine,
            artifact_integrity=integrity,
            target_inspector=adapter,
        )
        attempt_one = DatabaseReleasePublicationAttemptPreflight(
            engine,
            executor_id=executor_id,
            generate_attempt_id=generate_attempt_id,
            clock=clock,
        )
        create_one = DatabaseReleasePublicationImmutableCreate(
            engine,
            target_inspection=inspection,
            immutable_creator=adapter,
        )
        reconciliation = DatabaseReleasePublicationUnknownOutcomeReconciliation(
            engine, target_inspector=adapter
        )
        receipt = DatabaseReleasePublicationReconciliationFinalizer(
            engine,
            reconciliation=reconciliation,
            generate_receipt_id=generate_receipt_id,
            generate_reassessment_id=generate_reassessment_id,
            clock=clock,
        )
        recovery = DatabaseReleasePublicationRecoveryFinalizer(
            engine,
            reconciliation=reconciliation,
            generate_recovery_id=generate_recovery_id,
            generate_reassessment_id=generate_reassessment_id,
            clock=clock,
        )
        finalizer = DatabaseReleasePublicationCurrentOutcomeFinalizer(
            reconciliation=reconciliation,
            receipt_finalizer=receipt,
            recovery_finalizer=recovery,
        )
        attempt_two = DatabaseReleasePublicationRetryAttemptPreflight(
            engine,
            artifact_integrity=integrity,
            target_inspector=adapter,
            generate_attempt_id=generate_attempt_id,
            clock=clock,
        )
        create_two = DatabaseReleasePublicationRetryImmutableCreate(
            engine,
            artifact_integrity=integrity,
            target_inspector=adapter,
            immutable_creator=adapter,
        )
        worker = ProcessReleasePublicationWork(
            states=DatabaseReleasePublicationWorkStateLookup(engine),
            attempt_one=attempt_one,
            create_one=create_one,
            attempt_two=attempt_two,
            create_two=create_two,
            finalizer=finalizer,
        )
        return ReleasePublicationWorkerComposition(engine, provider, worker)
    except Exception:
        try:
            provider.close()
        except Exception:
            pass
        try:
            engine.dispose()
        except Exception:
            pass
        raise ReleasePublicationWorkerCompositionUnavailable from None
