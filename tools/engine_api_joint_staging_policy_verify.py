"""Policy-bound single-snapshot staging provenance verifier."""
import argparse
from datetime import datetime,timezone
import math,time
from pathlib import Path
from liquent_platform.persistence.identity_errors import ManifestHandoffRegistryUnavailable
from tools.engine_api_joint_staging_provenance_snapshot import load_policy_bound_snapshot,verify_policy_bound_snapshot

def verify(policy_file:Path,trust_file:Path,signature_file:Path,evidence_file:Path,receipt_file:Path,*artifact_files:Path,now:datetime)->None:
    try: verify_policy_bound_snapshot(load_policy_bound_snapshot(policy_file,trust_file,signature_file,evidence_file,receipt_file,*artifact_files),now=now)
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def _utc_now()->datetime:
    try:
        value=datetime.now(timezone.utc)
        if type(value)is not datetime or value.tzinfo is None or value.utcoffset().total_seconds()!=0: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def _monotonic_now()->float:
    try:
        value=time.monotonic()
        if type(value)is not float or not math.isfinite(value) or value<0: raise ManifestHandoffRegistryUnavailable
        return value
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def verify_current(policy_file:Path,trust_file:Path,signature_file:Path,evidence_file:Path,receipt_file:Path,*artifact_files:Path)->None:
    try: verify(policy_file,trust_file,signature_file,evidence_file,receipt_file,*artifact_files,now=_utc_now())
    except ManifestHandoffRegistryUnavailable: raise
    except Exception: raise ManifestHandoffRegistryUnavailable from None

def main(argv=None)->int:
    parser=argparse.ArgumentParser(add_help=False)
    for name in ("policy-file","trust-file","signature-file","evidence-file","receipt-file","render-file","inspect-file","health-file","staging-policy-file","shutdown-file"): parser.add_argument(f"--{name}",required=True,type=Path)
    try:
        value=parser.parse_args(argv);verify_current(value.policy_file,value.trust_file,value.signature_file,value.evidence_file,value.receipt_file,value.render_file,value.inspect_file,value.health_file,value.staging_policy_file,value.shutdown_file);return 0
    except (BaseException,): return 2

if __name__=="__main__": raise SystemExit(main())
