"""Explicit owner-controlled entrypoint for the joint Engine API runtime."""
from __future__ import annotations
import argparse
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_poll_runtime_composition import compose_manifest_handoff_supervisor_engine_api_health_poll_runtime
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings_source import load_manifest_handoff_supervisor_engine_api_health_run_settings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_settings_source import load_manifest_handoff_supervisor_engine_api_health_authority
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_joint_owner import JointManifestHandoffSupervisorEngineApiProcessOwner
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_joint_settings import load_manifest_handoff_supervisor_engine_api_joint_settings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_poll_runtime_composition import compose_manifest_handoff_supervisor_engine_api_poll_runtime
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings_source import load_manifest_handoff_supervisor_engine_api_proxy_settings

class _Parser(argparse.ArgumentParser):
    def error(self, message): raise ManifestHandoffRegistryUnavailable

def run_manifest_handoff_supervisor_engine_api_joint(settings_file: Path):
    try:
        settings = load_manifest_handoff_supervisor_engine_api_joint_settings(settings_file)
        proxy_settings = load_manifest_handoff_supervisor_engine_api_proxy_settings(settings.proxy_settings_file)
        authority = load_manifest_handoff_supervisor_engine_api_health_authority(settings.health_authority_file)
        health_settings = load_manifest_handoff_supervisor_engine_api_health_run_settings(settings.health_run_settings_file)
        proxy = compose_manifest_handoff_supervisor_engine_api_poll_runtime(proxy_settings, poll_timeout_seconds=settings.poll_timeout_seconds)
        health = compose_manifest_handoff_supervisor_engine_api_health_poll_runtime(proxy.observed_bundle, authority, health_settings, poll_timeout_seconds=settings.poll_timeout_seconds)
        return JointManifestHandoffSupervisorEngineApiProcessOwner(proxy, health, join_timeout_seconds=settings.join_timeout_seconds).run()
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None

def main(argv=None):
    parser = _Parser(prog="liquent-supervisor-engine-api-joint", add_help=False)
    parser.add_argument("--settings-file", required=True, type=Path)
    try:
        args = parser.parse_args(argv); run_manifest_handoff_supervisor_engine_api_joint(args.settings_file); return 0
    except Exception: return 2

if __name__ == "__main__":
    raise SystemExit(main())
