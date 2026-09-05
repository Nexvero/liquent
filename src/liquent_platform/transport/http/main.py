"""Production control-plane entry point."""

from __future__ import annotations

from pathlib import Path
from datetime import timedelta

import httpx2
import uvicorn

from liquent_platform.application.local_csv import LocalCsvMidBreakoutV0Resolver
from liquent_platform.application.internal_destination import (
    ValidatedInternalDestination,
)
from liquent_platform.application.manifest_handoff_supervisor_process_composition import (
    ManifestHandoffSupervisorCandidateReadinessProbe,
    compose_manifest_handoff_supervisor_candidate_process,
)
from liquent_platform.configuration import PlatformSettings
from liquent_platform.identity.manifest_handoff_supervisor_correlation import (
    ManifestHandoffSupervisorBackendInstanceId,
)
from liquent_platform.identity.oidc_verification_policy import OidcVerificationPolicy
from liquent_platform.observability.logging import configure_logging
from liquent_platform.persistence.database import build_engine
from liquent_platform.transport.http.app import create_app


def build_app(settings: PlatformSettings):
    """Build the configured app; local research remains explicit opt-in."""

    resolver = None
    if settings.research_data_root is not None:
        resolver = LocalCsvMidBreakoutV0Resolver(settings.research_data_root)
    dependencies = {"research_resolver": resolver}
    engine = None
    supervisor_process = None
    oidc_client = None
    if settings.manifest_handoff_supervisor_enabled:
        assert settings.database_url is not None
        assert settings.manifest_handoff_supervisor_backend_instance_id is not None
        engine = build_engine(settings.database_url.get_secret_value())
        try:
            supervisor_process = compose_manifest_handoff_supervisor_candidate_process(
                settings=settings,
                database_engine=engine,
                backend_instance_id=ManifestHandoffSupervisorBackendInstanceId(
                    settings.manifest_handoff_supervisor_backend_instance_id
                ),
            )
        except BaseException:
            engine.dispose()
            raise
        dependencies.update(
            database_engine=engine,
            database_engine_owned=True,
            manifest_handoff_supervisor_process=supervisor_process,
            manifest_handoff_supervisor_readiness=(
                ManifestHandoffSupervisorCandidateReadinessProbe(supervisor_process)
            ),
            manifest_handoff_supervisor_process_owned=True,
        )
    if not settings.oidc_enabled:
        try:
            return create_app(settings, **dependencies)
        except BaseException:
            if supervisor_process is not None:
                supervisor_process.close()
            if engine is not None:
                engine.dispose()
            raise

    rejection = ValidatedInternalDestination(settings.oidc_callback_rejection)
    unavailable = ValidatedInternalDestination(settings.oidc_callback_unavailable)
    policy = OidcVerificationPolicy(
        connect_timeout=timedelta(seconds=settings.oidc_connect_timeout_seconds),
        read_timeout=timedelta(seconds=settings.oidc_read_timeout_seconds),
        total_timeout=timedelta(seconds=settings.oidc_total_timeout_seconds),
        token_response_max_bytes=settings.oidc_token_response_max_bytes,
        jwks_response_max_bytes=settings.oidc_jwks_response_max_bytes,
        jwks_cache_ttl=timedelta(seconds=settings.oidc_jwks_cache_ttl_seconds),
    )
    oidc_client = httpx2.Client(trust_env=False, follow_redirects=False)
    try:
        return create_app(
            settings,
            **dependencies,
            oidc_http_client=oidc_client,
            oidc_http_client_owned=True,
            oidc_verification_policy=policy,
            oidc_login_origin=settings.oidc_login_origin,
            oidc_login_lifetime=timedelta(
                seconds=settings.oidc_login_lifetime_seconds
            ),
            oidc_session_lifetime=timedelta(
                seconds=settings.oidc_session_lifetime_seconds
            ),
            oidc_callback_rejection=rejection,
            oidc_callback_unavailable=unavailable,
        )
    except BaseException:
        oidc_client.close()
        if supervisor_process is not None:
            supervisor_process.close()
        if engine is not None:
            engine.dispose()
        raise


def main() -> None:
    settings = PlatformSettings(_secrets_dir=Path("/run/secrets"))
    configure_logging(settings.log_level.value, settings.log_format)
    uvicorn.run(
        build_app(settings),
        host=settings.http_host,
        port=settings.http_port,
        log_level=settings.log_level.value.lower(),
        access_log=True,
    )


if __name__ == "__main__":
    main()
