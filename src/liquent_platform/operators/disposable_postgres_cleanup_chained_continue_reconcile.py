"""Read-only reconciliation of an open chained-continuation claim."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import UTC,datetime,timedelta
from pathlib import Path
from liquent_platform.operators.disposable_postgres_cleanup_chained_continue import CHAIN,_auth as _chain_auth,_bind,_file,_historical_last
from liquent_platform.operators.disposable_postgres_cleanup_continue import _continuation_claim,_evidence_binding as _old_binding
from liquent_platform.operators.disposable_postgres_cleanup_finalize import _historical_reconciliation
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import _claim,_historical_cleanup,reconcile_disposable_postgres_cleanup
from liquent_platform.operators.disposable_postgres_cleanup_recontinue import _artifact,_binding2
from liquent_platform.operators.disposable_postgres_cleanup_recontinue_finalize import _binding3,_existing as _last_existing
from liquent_platform.operators.disposable_postgres_cleanup_recontinue_reconcile import _historical_recontinuation
from liquent_platform.operators.disposable_postgres_reconcile import _historical,_pairs,_timestamp
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT,IMAGE,OPAQUE,SHA256
ORDER={"container_removed":0,"application_network_removed":1,"runtime_removed_evidence_missing":2}
COMPARE=("chained_continuation_id",*CHAIN,"recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256","previous_resume_from","resume_from")
KEYS={"schema_version","chained_reconciliation_id",*COMPARE,"chained_continuation_authorization_sha256","operation","scope","executor_id","authorizer_id","valid_from","valid_until"}
class DisposablePostgresCleanupChainedContinueReconcileUnavailable(Exception):
    code="disposable_postgres_cleanup_chained_continue_reconcile_unavailable"
    def __init__(self):super().__init__(self.code)
class _Parser(argparse.ArgumentParser):
    def error(self,_):raise DisposablePostgresCleanupChainedContinueReconcileUnavailable
def _authorization(path,clock):
    try:
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs)
        if type(v) is not dict or set(v)!=KEYS or v["schema_version"]!=1 or v["phase"]!="disposable_postgres" or v["scope"]!="runtime_only" or v["operation"]!="inspect_disposable_postgres_cleanup_chained_continuation" or v["resume_from"] not in {"container_removed","application_network_removed"} or v["previous_resume_from"] not in {"container_removed","application_network_removed"}:raise ValueError
        for k in ("chained_reconciliation_id","chained_continuation_id","recontinuation_finalization_id","recontinuation_reconciliation_id","recontinuation_id","continuation_finalization_id","continuation_reconciliation_id","cleanup_continuation_id","cleanup_reconciliation_id","cleanup_id","run_id","reconciliation_id","claim_reconciliation_id","disposition_id","executor_id","authorizer_id"):
            if type(v[k]) is not str or not OPAQUE.fullmatch(v[k]):raise ValueError
        if v["executor_id"]==v["authorizer_id"] or not COMMIT.fullmatch(v["source_commit"]) or not IMAGE.fullmatch(v["image_ref"]):raise ValueError
        for k in ("compose_sha256","staging_evidence_sha256","reconciliation_evidence_sha256","claim_reconciliation_evidence_sha256","disposition_authorization_sha256","cleanup_authorization_sha256","cleanup_reconciliation_authorization_sha256","continuation_authorization_sha256","continuation_reconciliation_authorization_sha256","continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","recontinuation_authorization_sha256","recontinuation_reconciliation_authorization_sha256","recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256","chained_continuation_authorization_sha256"):
            if type(v[k]) is not str or not SHA256.fullmatch(v[k]):raise ValueError
        a,b,n=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]),clock()
        if type(n) is not datetime or n.tzinfo is None or b<=a or b-a>timedelta(hours=1) or not a<=n.astimezone(UTC)<=b:raise ValueError
        return v
    except Exception:raise DisposablePostgresCleanupChainedContinueReconcileUnavailable from None
def _historical_chain(path):
    try:v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _chain_auth(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupChainedContinueReconcileUnavailable from None
def _result(outcome):return (json.dumps({"operation":"disposable_postgres_cleanup_chained_continuation_reconciliation","outcome":outcome,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
def reconcile_disposable_postgres_cleanup_chained_continuation(*,docker_executable,authorization_file,reconciliation_file,claim_reconciliation_file,disposition_file,cleanup_file,cleanup_reconciliation_file,cleanup_continuation_file,continuation_reconciliation_file,continuation_finalization_file,recontinuation_file,recontinuation_reconciliation_file,recontinuation_finalization_file,chained_continuation_file,chained_reconciliation_file,staging_evidence_file,compose_file,runtime_environment_file,image_environment_file,project_name,evidence_directory,processes=None,clock=lambda:datetime.now(UTC)):
    try:
        original=_historical(authorization_file);cleanup=_historical_cleanup(cleanup_file);recon=_historical_reconciliation(cleanup_reconciliation_file);old=json.loads(_private_file(cleanup_continuation_file,32768),object_pairs_hook=_pairs);recont=_historical_recontinuation(recontinuation_file);last=_historical_last(recontinuation_finalization_file);previous=_historical_chain(chained_continuation_file);current=_authorization(chained_reconciliation_file,clock)
        if current["chained_continuation_authorization_sha256"]!=hashlib.sha256(_private_file(chained_continuation_file,32768)).hexdigest() or any(current[k]!=previous[k] for k in COMPARE) or original.run_id!=current["run_id"] or project_name!=f"liquent-{original.run_id}":raise ValueError
        lb=_binding3(last,recontinuation_finalization_file);ls=hashlib.sha256(last["recontinuation_finalization_id"].encode()).hexdigest();lp=evidence_directory/f"postgres-cleanup-recontinuation-finalization-{ls}.json";out=_last_existing(lp,lb);expected=last["resume_from"] if out=="recontinuation_attempt_finalized" else "application_network_removed" if out=="later_prefix_finalized" else None
        if current["recontinuation_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(lp,32768)).hexdigest() or current["resume_from"]!=expected:raise ValueError
        cb=_binding(original,cleanup,cleanup_file,project_name);cs=hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        if not _claim(evidence_directory/f".postgres-cleanup-{cs}.claim",cb):return _result("conflict")
        ob=_old_binding(old,cleanup_continuation_file,project_name);osx=hashlib.sha256(old["cleanup_continuation_id"].encode()).hexdigest();oc=evidence_directory/f".postgres-cleanup-continuation-{osx}.claim"
        if oc.exists():_continuation_claim(oc,ob);raise ValueError
        rb=_binding2(recont,recontinuation_file,project_name);rs=hashlib.sha256(recont["recontinuation_id"].encode()).hexdigest();rc=evidence_directory/f".postgres-cleanup-recontinuation-{rs}.claim"
        if rc.exists():_artifact(rc,rb);raise ValueError
        bind=_bind(previous,chained_continuation_file,project_name);stem=hashlib.sha256(previous["chained_continuation_id"].encode()).hexdigest();claim=evidence_directory/f".postgres-cleanup-chained-continuation-{stem}.claim";final=evidence_directory/f"postgres-cleanup-chained-continuation-{stem}.json"
        if _file(final,bind,True):return _result("chained_continuation_evidence_present")
        if not _file(claim,bind):return _result("not_found")
        a,b=_timestamp(recon["valid_from"]),_timestamp(recon["valid_until"]);raw=reconcile_disposable_postgres_cleanup(docker_executable=docker_executable,authorization_file=authorization_file,reconciliation_file=reconciliation_file,claim_reconciliation_file=claim_reconciliation_file,disposition_file=disposition_file,cleanup_file=cleanup_file,cleanup_reconciliation_file=cleanup_reconciliation_file,staging_evidence_file=staging_evidence_file,compose_file=compose_file,runtime_environment_file=runtime_environment_file,image_environment_file=image_environment_file,project_name=project_name,evidence_directory=evidence_directory,processes=processes,clock=lambda:a+(b-a)/2);obs=json.loads(raw,object_pairs_hook=_pairs)
        if type(obs) is not dict or set(obs)!={"schema_version","operation","outcome"} or obs["schema_version"]!=1 or obs["operation"]!="disposable_postgres_runtime_cleanup_reconciliation":raise ValueError
        state=obs["outcome"]
        if state not in ORDER or ORDER[state]<ORDER[current["resume_from"]]:return _result("conflict")
        if state==current["resume_from"]:return _result("chained_continuation_not_started")
        return _result(state)
    except DisposablePostgresCleanupChainedContinueReconcileUnavailable:raise
    except Exception:raise DisposablePostgresCleanupChainedContinueReconcileUnavailable from None
def main(argv=None):
    p=_Parser(prog="liquent-disposable-postgres-cleanup-chain-reconcile",add_help=False);names=("docker-executable","authorization-file","reconciliation-file","claim-reconciliation-file","disposition-file","cleanup-file","cleanup-reconciliation-file","cleanup-continuation-file","continuation-reconciliation-file","continuation-finalization-file","recontinuation-file","recontinuation-reconciliation-file","recontinuation-finalization-file","chained-continuation-file","chained-reconciliation-file","staging-evidence-file","compose-file","runtime-env-file","image-env-file","evidence-directory")
    for n in names:p.add_argument(f"--{n}",required=True,type=Path)
    p.add_argument("--project-name",required=True)
    try:v=vars(p.parse_args(argv));v["runtime_environment_file"]=v.pop("runtime_env_file");v["image_environment_file"]=v.pop("image_env_file");sys.stdout.buffer.write(reconcile_disposable_postgres_cleanup_chained_continuation(**v));return 0
    except Exception:return 2
if __name__=="__main__":raise SystemExit(main())
