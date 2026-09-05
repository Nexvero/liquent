"""Run- and image-bound fixed-root staging provenance verifier."""
import argparse
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools.engine_api_joint_staging_policy_verify import _utc_now
from tools.engine_api_joint_staging_provenance_snapshot import verify_run_bound_snapshot
from tools.engine_api_joint_staging_source_set import load_run_bound_source_set

def verify_current(root:Path)->None:
    try: verify_run_bound_snapshot(load_run_bound_source_set(root),now=_utc_now())
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def main(argv=None)->int:
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument("--source-root",required=True,type=Path)
    try: value=parser.parse_args(argv);verify_current(value.source_root);return 0
    except (BaseException,): return 2

if __name__=="__main__": raise SystemExit(main())
