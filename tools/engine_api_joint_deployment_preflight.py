"""Read-only validation of the four private joint Engine API settings files."""
from __future__ import annotations
import argparse
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_run_settings_source import load_manifest_handoff_supervisor_engine_api_health_run_settings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_health_settings_source import load_manifest_handoff_supervisor_engine_api_health_authority
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_joint_settings import load_manifest_handoff_supervisor_engine_api_joint_settings
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_settings_source import load_manifest_handoff_supervisor_engine_api_proxy_settings

def verify(joint_file: Path, proxy_file: Path, health_file: Path, health_run_file: Path) -> None:
    try:
        joint = load_manifest_handoff_supervisor_engine_api_joint_settings(joint_file)
        proxy = load_manifest_handoff_supervisor_engine_api_proxy_settings(proxy_file)
        health = load_manifest_handoff_supervisor_engine_api_health_authority(health_file)
        run = load_manifest_handoff_supervisor_engine_api_health_run_settings(health_run_file)
        expected = (Path("/run/liquent/config/engine-api-proxy.env"), Path("/run/liquent/config/engine-api-health.env"), Path("/run/liquent/config/engine-api-health-run.env"))
        if ((joint.proxy_settings_file, joint.health_authority_file, joint.health_run_settings_file) != expected
                or proxy.proxy_socket == health.socket_path
                or proxy.maximum_exchanges < 1 or run.maximum_exchanges < 1):
            raise ManifestHandoffRegistryUnavailable
    except ManifestHandoffRegistryUnavailable:
        raise
    except Exception:
        raise ManifestHandoffRegistryUnavailable from None

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    for name in ("joint-file", "proxy-file", "health-file", "health-run-file"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    try:
        values = parser.parse_args(argv)
        verify(values.joint_file, values.proxy_file, values.health_file, values.health_run_file)
        return 0
    except Exception:
        return 2

if __name__ == "__main__": raise SystemExit(main())
