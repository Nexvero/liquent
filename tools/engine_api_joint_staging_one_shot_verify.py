"""Verify a run-bound source root and durably accept its run once."""
import argparse
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_acceptance import build_staging_run_acceptance,load_staging_run_acceptance,observe_staging_run_acceptance,record_staging_run_acceptance,verify_staging_run_acceptance
from liquent_platform.transport.manifest_handoff_supervisor_engine_api_staging_run import decode_staging_run_authority
from tools.engine_api_joint_staging_policy_verify import _monotonic_now,_utc_now
from tools.engine_api_joint_staging_provenance_snapshot import verify_run_bound_snapshot
from tools.engine_api_joint_staging_source_set import observe_run_bound_source_set

def verify_and_accept(source_root:Path,acceptance_root:Path,*,expected_source_identity:tuple[int,int]|None=None,expected_acceptance_identity:tuple[int,int]|None=None):
    try:
        source_observed=observe_run_bound_source_set(source_root,expected_root_identity=expected_source_identity);snapshot=source_observed.snapshot;authority=decode_staging_run_authority(snapshot.run_authority);current=load_staging_run_acceptance(acceptance_root,authority.run_id,expected_root_identity=expected_acceptance_identity)
        if current is not None: verify_staging_run_acceptance(current,authority,snapshot.run_envelope);raise ManifestHandoffRegistryUnavailable
        initial_now=_utc_now();initial_monotonic=_monotonic_now();verify_run_bound_snapshot(snapshot,now=initial_now);acceptance=build_staging_run_acceptance(authority,snapshot.run_envelope);recorded=record_staging_run_acceptance(acceptance_root,acceptance,expected_root_identity=expected_acceptance_identity)
        if observe_run_bound_source_set(source_root,expected_root_identity=expected_source_identity)!=source_observed: raise ManifestHandoffRegistryUnavailable
        final=load_staging_run_acceptance(acceptance_root,authority.run_id,expected_root_identity=expected_acceptance_identity)
        if final!=acceptance: raise ManifestHandoffRegistryUnavailable
        final_observed=observe_staging_run_acceptance(acceptance_root,authority.run_id,expected_root_identity=expected_acceptance_identity)
        if final_observed!=recorded: raise ManifestHandoffRegistryUnavailable
        final_monotonic=_monotonic_now();final_now=_utc_now()
        if final_now<initial_now or final_monotonic<initial_monotonic or final_monotonic-initial_monotonic>30: raise ManifestHandoffRegistryUnavailable
        verify_run_bound_snapshot(snapshot,now=final_now)
        return final_observed
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def main(argv=None)->int:
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument("--source-root",required=True,type=Path);parser.add_argument("--acceptance-root",required=True,type=Path)
    try: value=parser.parse_args(argv);verify_and_accept(value.source_root,value.acceptance_root);return 0
    except (BaseException,): return 2

if __name__=="__main__": raise SystemExit(main())
