"""Read-only acceptance registry and accepted-source audit."""
import argparse
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import inspect_staging_run_acceptance_registry,observe_staging_run_acceptance,observe_staging_run_acceptance_registry,verify_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tools.engine_api_joint_staging_policy_verify import _monotonic_now,_utc_now
from tools.engine_api_joint_staging_provenance_snapshot import verify_run_bound_snapshot
from tools.engine_api_joint_staging_source_set import observe_run_bound_source_set

def inspect_registry(acceptance_root:Path,*,expected_acceptance_identity:tuple[int,int]|None=None):
    return inspect_staging_run_acceptance_registry(acceptance_root,expected_root_identity=expected_acceptance_identity)

def observe_registry(acceptance_root:Path,*,expected_acceptance_identity:tuple[int,int]|None=None):
    return observe_staging_run_acceptance_registry(acceptance_root,expected_root_identity=expected_acceptance_identity)

def verify_accepted_current(source_root:Path,acceptance_root:Path,*,expected_source_identity:tuple[int,int]|None=None,expected_acceptance_identity:tuple[int,int]|None=None):
    try:
        source_observed=observe_run_bound_source_set(source_root,expected_root_identity=expected_source_identity);snapshot=source_observed.snapshot;authority=decode_staging_run_authority(snapshot.run_authority);observed=observe_staging_run_acceptance(acceptance_root,authority.run_id,expected_root_identity=expected_acceptance_identity)
        if observed is None: raise ManifestHandoffRegistryUnavailable
        initial_now=_utc_now();initial_monotonic=_monotonic_now();verify_staging_run_acceptance(observed.acceptance,authority,snapshot.run_envelope);verify_run_bound_snapshot(snapshot,now=initial_now)
        if observe_run_bound_source_set(source_root,expected_root_identity=expected_source_identity)!=source_observed: raise ManifestHandoffRegistryUnavailable
        final=observe_staging_run_acceptance(acceptance_root,authority.run_id,expected_root_identity=expected_acceptance_identity)
        if final!=observed: raise ManifestHandoffRegistryUnavailable
        final_monotonic=_monotonic_now();final_now=_utc_now()
        if final_now<initial_now or final_monotonic<initial_monotonic or final_monotonic-initial_monotonic>30: raise ManifestHandoffRegistryUnavailable
        verify_run_bound_snapshot(snapshot,now=final_now)
        return source_observed,final
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def main(argv=None)->int:
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument("--acceptance-root",required=True,type=Path);parser.add_argument("--source-root",type=Path)
    try:
        value=parser.parse_args(argv)
        if value.source_root is None: inspect_registry(value.acceptance_root)
        else: verify_accepted_current(value.source_root,value.acceptance_root)
        return 0
    except (BaseException,): return 2

if __name__=="__main__": raise SystemExit(main())
