"""Authoritative cleanup-retention evaluation from the active policy."""

from collections.abc import Callable
from datetime import datetime, timezone

from liquent_platform.identity.manifest_handoff_supervisor_control_directory import (
    RetiredManifestHandoffSupervisorControlDirectory,
)
from liquent_platform.identity.manifest_handoff_supervisor_control_directory_cleanup import (
    ManifestHandoffSupervisorControlDirectoryCleanupDisposition,
)
from liquent_platform.identity.manifest_handoff_supervisor_cleanup_retention import (
    EvaluateManifestHandoffSupervisorControlDirectoryRetention,
    EvaluatedManifestHandoffSupervisorControlDirectoryRetention,
    ManifestHandoffSupervisorCleanupRetentionDataClass,
)
from liquent_platform.identity.ports import (
    ManifestHandoffSupervisorCleanupRetentionPolicyLookup,
)
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable


class AuthoritativeManifestHandoffSupervisorCleanupRetentionEvaluation:
    """Evaluate one exact retired value against one freshly resolved policy."""

    __slots__ = ("_policies", "_clock")

    def __init__(self, policies: ManifestHandoffSupervisorCleanupRetentionPolicyLookup,
                 *, clock: Callable[[], datetime]) -> None:
        if not callable(clock) or not callable(
            getattr(policies, "resolve_active_cleanup_retention_policy", None)
        ):
            raise ManifestHandoffRegistryUnavailable
        self._policies = policies
        self._clock = clock

    def __repr__(self) -> str:
        return "AuthoritativeManifestHandoffSupervisorCleanupRetentionEvaluation()"

    def evaluate_control_directory_retention(self, request, retired):
        if (type(request) is not EvaluateManifestHandoffSupervisorControlDirectoryRetention
                or type(retired) is not RetiredManifestHandoffSupervisorControlDirectory):
            raise ManifestHandoffRegistryUnavailable
        if request.directory_id != retired.directory_id:
            return None
        active = self._policies.resolve_active_cleanup_retention_policy()
        if active is None:
            return None
        evaluated_at = self._clock()
        if (type(evaluated_at) is not datetime or evaluated_at.tzinfo is None
                or evaluated_at.utcoffset() != timezone.utc.utcoffset(evaluated_at)
                or evaluated_at < retired.retired_at
                or evaluated_at < active.activated_at):
            raise ManifestHandoffRegistryUnavailable
        disposition = (
            ManifestHandoffSupervisorControlDirectoryCleanupDisposition.ELIGIBLE
            if evaluated_at >= retired.retired_at + active.policy.minimum_retention
            else ManifestHandoffSupervisorControlDirectoryCleanupDisposition.RETAIN
        )
        try:
            return EvaluatedManifestHandoffSupervisorControlDirectoryRetention(
                request, retired,
                ManifestHandoffSupervisorCleanupRetentionDataClass.SUPERVISOR_CONTROL_DIRECTORY,
                active.policy.revision_id, disposition, evaluated_at,
            )
        except (TypeError, ValueError, OverflowError):
            raise ManifestHandoffRegistryUnavailable from None
