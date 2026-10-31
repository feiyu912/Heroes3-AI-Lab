"""Copy verified completed chain deliverables to a fresh G directory; preserve Linux originals."""
import collections,hashlib,json,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;POLICY=HERE.parent.parent
sys.path.insert(0,str(POLICY))
from model_io import read,load_model,tensor_sha
ROOT=Path('/root/heroes3-ai-lab/evaluations/strategic-build-exploration-continuation-01')
BASE=Path('/root/heroes3-ai-lab/evaluations/strategic-learned-build-exploration-train-01')
FINAL='24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(path):return json.loads(Path(path).read_text())
def main():
    out=HERE/'delivery'
    if out.exists():raise FileExistsError('Refuse overwrite '+str(out))
    chain=get(HERE/'inspection-02/AUDIT.json');assert chain['all3_updates_completed_and_verified'] and chain['cumulative_steps_last_verified']==504
    gpu=POLICY/'recovery-audit-01/native-cuda-update4-01/AUDIT.json';gp=get(gpu)
    assert gp['passed_exact'] and gp['checkpoint_sha256']==FINAL and gp['optimizer_steps_restored']==504 and len(gp['negative_cases'])==6
    original=get(POLICY/'recovery-audit-01/train-distribution-01/AUDIT.json');assert original['states']==1891 and original['actual_policy_builds']==28
    for f,h in get(HERE/'inspection-02/INPUT_RECHECK.json').items():assert sha(f)==h
    for f,h in get(POLICY/'recovery-audit-01/train-distribution-01/FROZEN_INPUT_RECHECK.json').items():assert sha(f)==h
    b0,h0=read(BASE/'update-01/update-1.pt')
    assert h0==chain['fixed_parent_sha256'] and b0['lineage']['explicit_optimizer_reset'] is True
    entries=[dict(update=1,samples=1891,policy_builds=28,actual_build_categories=original['actual_build_categories'],
        training_wins=4,training_losses=4,build_bias=original['build_bias_after'],
        new_CUDA_optimizer_steps=120,cumulative_same_optimizer_steps=120,explicit_optimizer_reset=True,
        checkpoint_sha256=h0,protocol_sha256=b0['protocol_sha256'])]+chain['inspected_complete_updates']
    assert all(e['protocol_sha256']==chain['protocol_sha256'] for e in entries)
    categories=collections.Counter()
    for e in entries:categories.update(e['actual_build_categories'])
    total_samples=sum(e['samples'] for e in entries);total_builds=sum(e['policy_builds'] for e in entries)
    assert total_samples==8012 and total_builds==130 and categories['income']==6
    copies=[(ROOT/'PLAN.json','controller/PLAN.json'),(ROOT/'RESULT.json','controller/RESULT.json'),
        (BASE/'update-01/PLAN.json','update-01/PLAN.json'),(BASE/'update-01/RESULT.json','update-01/RESULT.json'),
        (HERE/'inspection-02/AUDIT.json','verification/CPU_CHAIN_AUDIT.json'),
        (HERE/'inspection-02/INPUT_RECHECK.json','verification/CPU_CHAIN_INPUT_RECHECK.json'),
        (gpu,'verification/GPU_RECOVERY_AUDIT.json'),
        (POLICY/'recovery-audit-01/train-distribution-01/AUDIT.json','verification/UPDATE1_TRAIN_AUDIT.json'),
        (HERE/'check_chain_cpu.py','verification/check_chain_cpu.py'),(Path(__file__),'verification/deliver.py')]
    for update in (2,3,4):
        root=ROOT/f'round-{update:02d}'
        for name in ('PLAN.json','RESULT.json'):copies.append((root/'update'/name,f'update-{update:02d}/{name}'))
        for index in range(8):
            for name in ('AUDIT.json','episode.json'):copies.append((root/f'cell-{index:02d}/admitted'/name,f'update-{update:02d}/cell-{index:02d}/{name}'))
    final=ROOT/'round-04/update/update-4.pt';assert sha(final)==FINAL
    copies.append((final,'model/update-4.pt'))
    frozen={str(src):sha(src) for src,_ in copies}
    out.mkdir()
    manifest=[]
    for source,relative in copies:
        dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():raise FileExistsError(dest)
        shutil.copy2(source,dest);digest=sha(dest);assert digest==frozen[str(source)]==sha(source)
        manifest.append(dict(source=str(source),target=relative,sha256=digest,bytes=dest.stat().st_size,original_preserved=True))
    model,bundle,digest=load_model(out/'model/update-4.pt','cpu')
    assert digest==FINAL and bundle['optimizer_steps_total']==504 and tensor_sha(model.state_dict())==bundle['policy_tensor_sha256']
    assert all(sha(src)==h for src,h in frozen.items())
    report=dict(passed=True,refused_overwrite=True,original_Linux_evidence_preserved=True,CPU_only=True,new_native_games=0,audit_optimizer_steps=0,
        final_model_sha256=FINAL,copied_checkpoint_CPU_load_exact=True,epochs=entries,
        total_Training_games=32,total_Training_samples=total_samples,total_true_policy_builds=total_builds,
        actual_build_categories=dict(categories),total_income_builds=categories['income'],
        same_optimizer_total_steps=504,ancestor188_not_added_to_this_optimizer=True,
        training_wins=16,training_losses=16,independent_ability_improvement_claim=False,
        original_saved_protocol_sha256=chain['protocol_sha256'],external_controller_not_part_of_original_saved_protocol=True,
        copied_files=manifest)
    (out/'DELIVERY_MANIFEST.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'README.md').write_text('# Verified strategic training checkpoint\n\nFinal model: model/update-4.pt, SHA256 '+FINAL+'.\n\n'
        '32 complete Training games,8012 policy rows,130 actual builds (98 infrastructure,26 dwelling,6 income). Four updates in this optimizer epoch total504 Adam steps; ancestor188 belongs to an earlier reset epoch and is not added. Update1 explicitly reset Adam; updates2/3/4 restored and continued the same optimizer and exact protocol.\n\n'
        'All three continuation rounds and the copied CPU checkpoint were verified; original Linux evidence is retained. Root independently completed actual CUDA model/Adam/stop/build-moment/RNG restoration with six invalid-resume rejection checks; copied evidence is verification/GPU_RECOVERY_AUDIT.json.\n\n'
        'These are training and recovery facts, not a claim of stronger independent performance. Separate fixed paired DEV remains the capability assessment. DELIVERY_MANIFEST.json binds every copied source and destination SHA.\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('epochs','copied_files')},indent=2))
    print(json.dumps({'copied_files':len(manifest),'delivery':str(out),'manifest_sha256':sha(out/'DELIVERY_MANIFEST.json')},indent=2))
if __name__=='__main__':main()
