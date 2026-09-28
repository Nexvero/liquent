"""Read-only reconciliation of an open generation-bound continuation claim."""
from __future__ import annotations
import argparse,hashlib,json,sys
from datetime import UTC,datetime,timedelta
from pathlib import Path
from liquent_platform.operators.disposable_postgres_cleanup_generation_continue import ROOT,_auth as _generation_auth,_bind,_file,_lineage
from liquent_platform.operators.disposable_postgres_cleanup_chained_continue import _bind as _chain_bind,_file as _chain_file
from liquent_platform.operators.disposable_postgres_cleanup_chained_continue_finalize import _authorization as _final_auth,_binding4,_existing as _final_existing
from liquent_platform.operators.disposable_postgres_cleanup_continue import _continuation_claim,_evidence_binding as _old_binding
from liquent_platform.operators.disposable_postgres_cleanup_finalize import _historical_reconciliation
from liquent_platform.operators.disposable_postgres_cleanup_reconcile import _claim,_historical_cleanup,reconcile_disposable_postgres_cleanup
from liquent_platform.operators.disposable_postgres_cleanup_recontinue import _artifact,_binding2
from liquent_platform.operators.disposable_postgres_cleanup_recontinue_reconcile import _historical_recontinuation
from liquent_platform.operators.disposable_postgres_reconcile import _historical,_pairs,_timestamp
from liquent_platform.operators.disposable_postgres_runtime_cleanup import _binding
from liquent_platform.operators.research_worker_configuration import _private_file
from liquent_platform.operators.research_worker_staging_executor import COMMIT,IMAGE,OPAQUE,SHA256
ORDER={"container_removed":0,"application_network_removed":1,"runtime_removed_evidence_missing":2}
COMPARE=("generation_continuation_id","generation","predecessor_kind","predecessor_generation",*ROOT,"predecessor_resume_from","predecessor_finalization_authorization_sha256","predecessor_finalization_evidence_sha256","resume_from")
KEYS={"schema_version","generation_reconciliation_id",*COMPARE,"generation_continuation_authorization_sha256","operation","scope","executor_id","authorizer_id","valid_from","valid_until"}
class DisposablePostgresCleanupGenerationContinueReconcileUnavailable(Exception):
    code="disposable_postgres_cleanup_generation_continue_reconcile_unavailable"
    def __init__(self):super().__init__(self.code)
class _Parser(argparse.ArgumentParser):
    def error(self,_):raise DisposablePostgresCleanupGenerationContinueReconcileUnavailable
def _authorization(path,clock):
    try:
        v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs)
        if type(v) is not dict or set(v)!=KEYS or v["schema_version"]!=1 or v["phase"]!="disposable_postgres" or v["scope"]!="runtime_only" or v["operation"]!="inspect_disposable_postgres_cleanup_generation_continuation" or v["resume_from"] not in ORDER or v["resume_from"]=="runtime_removed_evidence_missing" or v["predecessor_resume_from"] not in {"container_removed","application_network_removed"} or type(v["generation"]) is not int or v["generation"]<1 or type(v["predecessor_generation"]) is not int or v["predecessor_kind"] not in {"lq362","repeatable_generation"} or (v["generation"]==1)!=(v["predecessor_kind"]=="lq362") or v["predecessor_generation"]!=v["generation"]-1:raise ValueError
        for k in ("generation_reconciliation_id","generation_continuation_id","chained_finalization_id","chained_reconciliation_id","chained_continuation_id","recontinuation_finalization_id","recontinuation_reconciliation_id","recontinuation_id","continuation_finalization_id","continuation_reconciliation_id","cleanup_continuation_id","cleanup_reconciliation_id","cleanup_id","run_id","reconciliation_id","claim_reconciliation_id","disposition_id","executor_id","authorizer_id"):
            if type(v[k]) is not str or not OPAQUE.fullmatch(v[k]):raise ValueError
        if v["executor_id"]==v["authorizer_id"] or not COMMIT.fullmatch(v["source_commit"]) or not IMAGE.fullmatch(v["image_ref"]):raise ValueError
        for k in ("compose_sha256","staging_evidence_sha256","reconciliation_evidence_sha256","claim_reconciliation_evidence_sha256","disposition_authorization_sha256","cleanup_authorization_sha256","cleanup_reconciliation_authorization_sha256","continuation_authorization_sha256","continuation_reconciliation_authorization_sha256","continuation_finalization_authorization_sha256","continuation_finalization_evidence_sha256","recontinuation_authorization_sha256","recontinuation_reconciliation_authorization_sha256","recontinuation_finalization_authorization_sha256","recontinuation_finalization_evidence_sha256","chained_continuation_authorization_sha256","chained_reconciliation_authorization_sha256","predecessor_finalization_authorization_sha256","predecessor_finalization_evidence_sha256","generation_continuation_authorization_sha256"):
            if type(v[k]) is not str or not SHA256.fullmatch(v[k]):raise ValueError
        a,b,n=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]),clock()
        if type(n) is not datetime or n.tzinfo is None or b<=a or b-a>timedelta(hours=1) or not a<=n.astimezone(UTC)<=b:raise ValueError
        return v
    except Exception:raise DisposablePostgresCleanupGenerationContinueReconcileUnavailable from None
def _historical_generation(path):
    try:v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _generation_auth(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupGenerationContinueReconcileUnavailable from None
def _historical_final(path):
    try:v=json.loads(_private_file(path,32768),object_pairs_hook=_pairs);a,b=_timestamp(v["valid_from"]),_timestamp(v["valid_until"]);return _final_auth(path,lambda:a+(b-a)/2)
    except Exception:raise DisposablePostgresCleanupGenerationContinueReconcileUnavailable from None
def _result(outcome):return (json.dumps({"operation":"disposable_postgres_cleanup_generation_continuation_reconciliation","outcome":outcome,"schema_version":1},sort_keys=True,separators=(",",":"))+"\n").encode()
def reconcile_disposable_postgres_cleanup_generation_continuation(*,docker_executable,authorization_file,reconciliation_file,claim_reconciliation_file,disposition_file,cleanup_file,cleanup_reconciliation_file,cleanup_continuation_file,continuation_reconciliation_file,continuation_finalization_file,recontinuation_file,recontinuation_reconciliation_file,recontinuation_finalization_file,chained_continuation_file,chained_finalization_file,generation_continuation_file,generation_reconciliation_file,staging_evidence_file,compose_file,runtime_environment_file,image_environment_file,project_name,evidence_directory,predecessor_generation_continuation_file=None,predecessor_generation_finalization_file=None,generation_lineage_continuation_files=None,generation_lineage_finalization_files=None,processes=None,clock=lambda:datetime.now(UTC)):
    try:
        original=_historical(authorization_file);cleanup=_historical_cleanup(cleanup_file);recon=_historical_reconciliation(cleanup_reconciliation_file);old=json.loads(_private_file(cleanup_continuation_file,32768),object_pairs_hook=_pairs);recont=_historical_recontinuation(recontinuation_file);chain=json.loads(_private_file(chained_continuation_file,32768),object_pairs_hook=_pairs);previous=_historical_generation(generation_continuation_file);current=_authorization(generation_reconciliation_file,clock)
        if current["generation_continuation_authorization_sha256"]!=hashlib.sha256(_private_file(generation_continuation_file,32768)).hexdigest() or any(current[k]!=previous[k] for k in COMPARE) or original.run_id!=current["run_id"] or project_name!=f"liquent-{original.run_id}":raise ValueError
        if current["generation"]==1:
            if predecessor_generation_continuation_file is not None or predecessor_generation_finalization_file is not None or generation_lineage_continuation_files or generation_lineage_finalization_files:raise ValueError
            last=_historical_final(chained_finalization_file);lb=_binding4(last,chained_finalization_file);ls=hashlib.sha256(last["chained_finalization_id"].encode()).hexdigest();lp=evidence_directory/f"postgres-cleanup-chained-continuation-finalization-{ls}.json";out=_final_existing(lp,lb);attempt="chained_continuation_attempt_finalized";allowed={attempt,"later_prefix_finalized"};auth_file=chained_finalization_file
        elif current["generation"]==2:
            if predecessor_generation_continuation_file is None or predecessor_generation_finalization_file is None or generation_lineage_continuation_files or generation_lineage_finalization_files:raise ValueError
            predecessor=_historical_generation(predecessor_generation_continuation_file)
            from liquent_platform.operators.disposable_postgres_cleanup_generation_continue import _historical_generation_final
            from liquent_platform.operators.disposable_postgres_cleanup_generation_continue_finalize import _binding5,_existing
            last=_historical_generation_final(predecessor_generation_finalization_file)
            if predecessor["generation"]!=1 or last["generation"]!=1 or current["predecessor_resume_from"]!=predecessor["resume_from"]:raise ValueError
            lb=_binding5(last,predecessor_generation_finalization_file);ls=hashlib.sha256(last["generation_finalization_id"].encode()).hexdigest();lp=evidence_directory/f"postgres-cleanup-generation-continuation-finalization-{ls}.json";out=_existing(lp,lb);attempt="generation_continuation_attempt_finalized";allowed={attempt,"later_prefix_finalized"};auth_file=predecessor_generation_finalization_file
            pb=_bind(predecessor,predecessor_generation_continuation_file,project_name);ps=hashlib.sha256(predecessor["generation_continuation_id"].encode()).hexdigest();pc=evidence_directory/f".postgres-cleanup-generation-continuation-{ps}.claim"
            if pc.exists():_file(pc,pb);raise ValueError
        else:
            if predecessor_generation_continuation_file is not None or predecessor_generation_finalization_file is not None:raise ValueError
            predecessor,last,lp,out=_lineage(current,generation_lineage_continuation_files,generation_lineage_finalization_files,chained_finalization_file,evidence_directory,project_name);attempt="generation_continuation_attempt_finalized";allowed={attempt,"later_prefix_finalized"};auth_file=tuple(generation_lineage_finalization_files or ())[-1]
        expected=current["predecessor_resume_from"] if out==attempt else "application_network_removed" if out=="later_prefix_finalized" else None
        if out not in allowed or current["predecessor_finalization_authorization_sha256"]!=hashlib.sha256(_private_file(auth_file,32768)).hexdigest() or current["predecessor_finalization_evidence_sha256"]!=hashlib.sha256(_private_file(lp,32768)).hexdigest() or current["resume_from"]!=expected:raise ValueError
        cb=_binding(original,cleanup,cleanup_file,project_name);cs=hashlib.sha256(cleanup["cleanup_id"].encode()).hexdigest()
        if not _claim(evidence_directory/f".postgres-cleanup-{cs}.claim",cb):return _result("conflict")
        ob=_old_binding(old,cleanup_continuation_file,project_name);osx=hashlib.sha256(old["cleanup_continuation_id"].encode()).hexdigest();oc=evidence_directory/f".postgres-cleanup-continuation-{osx}.claim"
        if oc.exists():_continuation_claim(oc,ob);raise ValueError
        rb=_binding2(recont,recontinuation_file,project_name);rs=hashlib.sha256(recont["recontinuation_id"].encode()).hexdigest();rc=evidence_directory/f".postgres-cleanup-recontinuation-{rs}.claim"
        if rc.exists():_artifact(rc,rb);raise ValueError
        chainbind=_chain_bind(chain,chained_continuation_file,project_name);chains=hashlib.sha256(chain["chained_continuation_id"].encode()).hexdigest();chainclaim=evidence_directory/f".postgres-cleanup-chained-continuation-{chains}.claim"
        if chainclaim.exists():_chain_file(chainclaim,chainbind);raise ValueError
        bind=_bind(previous,generation_continuation_file,project_name);stem=hashlib.sha256(previous["generation_continuation_id"].encode()).hexdigest();claim=evidence_directory/f".postgres-cleanup-generation-continuation-{stem}.claim";final=evidence_directory/f"postgres-cleanup-generation-continuation-{stem}.json"
        if _file(final,bind,True):return _result("generation_continuation_evidence_present")
        if not _file(claim,bind):return _result("not_found")
        a,b=_timestamp(recon["valid_from"]),_timestamp(recon["valid_until"]);raw=reconcile_disposable_postgres_cleanup(docker_executable=docker_executable,authorization_file=authorization_file,reconciliation_file=reconciliation_file,claim_reconciliation_file=claim_reconciliation_file,disposition_file=disposition_file,cleanup_file=cleanup_file,cleanup_reconciliation_file=cleanup_reconciliation_file,staging_evidence_file=staging_evidence_file,compose_file=compose_file,runtime_environment_file=runtime_environment_file,image_environment_file=image_environment_file,project_name=project_name,evidence_directory=evidence_directory,processes=processes,clock=lambda:a+(b-a)/2);obs=json.loads(raw,object_pairs_hook=_pairs)
        if type(obs) is not dict or set(obs)!={"schema_version","operation","outcome"} or obs["schema_version"]!=1 or obs["operation"]!="disposable_postgres_runtime_cleanup_reconciliation":raise ValueError
        state=obs["outcome"]
        if state not in ORDER or ORDER[state]<ORDER[current["resume_from"]]:return _result("conflict")
        if state==current["resume_from"]:return _result("generation_continuation_not_started")
        return _result(state)
    except DisposablePostgresCleanupGenerationContinueReconcileUnavailable:raise
    except Exception:raise DisposablePostgresCleanupGenerationContinueReconcileUnavailable from None
def main(argv=None):
    p=_Parser(prog="liquent-disposable-postgres-cleanup-generation-reconcile",add_help=False);names=("docker-executable","authorization-file","reconciliation-file","claim-reconciliation-file","disposition-file","cleanup-file","cleanup-reconciliation-file","cleanup-continuation-file","continuation-reconciliation-file","continuation-finalization-file","recontinuation-file","recontinuation-reconciliation-file","recontinuation-finalization-file","chained-continuation-file","chained-finalization-file","generation-continuation-file","generation-reconciliation-file","staging-evidence-file","compose-file","runtime-env-file","image-env-file","evidence-directory")
    for n in names:p.add_argument(f"--{n}",required=True,type=Path)
    p.add_argument("--predecessor-generation-continuation-file",type=Path);p.add_argument("--predecessor-generation-finalization-file",type=Path);p.add_argument("--generation-lineage-continuation-file",dest="generation_lineage_continuation_files",action="append",type=Path);p.add_argument("--generation-lineage-finalization-file",dest="generation_lineage_finalization_files",action="append",type=Path)
    p.add_argument("--project-name",required=True)
    try:v=vars(p.parse_args(argv));v["runtime_environment_file"]=v.pop("runtime_env_file");v["image_environment_file"]=v.pop("image_env_file");sys.stdout.buffer.write(reconcile_disposable_postgres_cleanup_generation_continuation(**v));return 0
    except Exception:return 2
if __name__=="__main__":raise SystemExit(main())
