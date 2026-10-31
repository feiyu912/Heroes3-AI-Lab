"""Train-only policy saturation audit; no optimizer and no sample admission."""
import hashlib,json,sys,subprocess,fcntl,statistics
from pathlib import Path
import torch
HERE=Path(__file__).resolve().parent
TRAIN=HERE.parent/'strategic-typed-training-v1'
sys.path.insert(0,str(TRAIN))
from load_admitted import load
from model_io import load_model
from episode_balanced_ppo import collate
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    torch.set_num_threads(1)
    result_path=TRAIN/'balanced-ack-certified-01/RESULT.json'
    sealed=json.loads(result_path.read_text());assert sealed['passed'] and len(sealed['episodes'])==8
    samples=[];proofs={str(result_path):sha(result_path)}
    for entry in sealed['episodes']:
        directory=Path(entry['admission']);assert sha(directory/'AUDIT.json')==entry['admission_sha256']
        rows,episodes,report=load(directory)
        assert all(e['job']['map'] in ('takeover-v2-train-01-mines','takeover-v2-train-02-development') for e in episodes)
        samples.extend(rows);proofs[str(directory/'AUDIT.json')]=sha(directory/'AUDIT.json')
    assert len(samples)==sealed['rows']==2588
    checkpoint=TRAIN/'cuda-curriculum-ack-01/update-1.pt'
    model,bundle,digest=load_model(checkpoint,'cpu')
    assert digest=='539850b6552a97adb10425605d7eebc065cf60d799a192833227cb2cb220bcc3'
    variants={str(t):{'stop':[],'entropy':[],'move_entropy':[],'top_probability':[],'forward_kl':[]} for t in (1,2,4,8)}
    one_move=0;multiple_move=0;argmax_equal={str(t):True for t in (1,2,4,8)}
    with torch.no_grad():
        for sample in samples:
            request=sample['request'];logits,_=model(**collate([request],'cpu'))
            logits=logits[0].double();p=torch.softmax(logits,0);logp=torch.log_softmax(logits,0)
            stop=[i for i,c in enumerate(request['candidates']) if c['op']=='end_turn'];moves=[i for i,c in enumerate(request['candidates']) if c['op']=='move']
            assert len(stop)==1 and len(moves)>=1
            one_move+=len(moves)==1;multiple_move+=len(moves)>1
            for t in (1,2,4,8):
                q=torch.softmax(logits/t,0);logq=torch.log_softmax(logits/t,0);v=variants[str(t)]
                v['stop'].append(float(q[stop[0]]));v['entropy'].append(float(-(q*logq).sum()))
                v['top_probability'].append(float(q.max()));v['forward_kl'].append(float((p*(logp-logq)).sum()))
                if len(moves)>1:
                    m=torch.softmax(logits[moves]/t,0);v['move_entropy'].append(float(-(m*torch.log_softmax(logits[moves]/t,0)).sum()))
                argmax_equal[str(t)] &= int(logits.argmax())==int((logits/t).argmax())
    summarized={}
    for t,v in variants.items():
        summarized[t]={key:{'mean':statistics.mean(values),'median':statistics.median(values),'min':min(values),'max':max(values)} for key,values in v.items()}
        summarized[t]['argmax_unchanged']=argmax_equal[t]
        summarized[t]['eligible']=int(t)>1 and .01<=summarized[t]['stop']['mean']<=.1 and summarized[t]['move_entropy']['median']>=.15 and summarized[t]['forward_kl']['mean']<=.5
    chosen=next((int(t) for t,v in summarized.items() if v['eligible']),None)
    processes=subprocess.check_output(['ps','-eo','pid,comm,args'],text=True)
    active=[line for line in processes.splitlines() if any(k in line for k in ('vcmiclient','vcmiserver','ninja','train_update','collect_episode')) and 'audit_train_exploration.py' not in line and 'bash -lc' not in line]
    handles=[]
    for name in ('.gpu-learner-lock','.pool-lock'):
        handle=(Path('/root/heroes3-ai-lab/evaluations')/name).open('a+');handles.append(handle);fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
    gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
    out=HERE/'train-exploration-audit-01';out.mkdir(exist_ok=False)
    proofs.update({str(checkpoint):digest,str(Path(__file__)):sha(__file__),str(HERE/'PLAN.md'):sha(HERE/'PLAN.md')})
    report={'passed':True,'scope':'TRAIN observations only; probability analysis, no gradient/new games/training rows','rows':len(samples),'one_move_plus_stop':one_move,'multiple_move_plus_stop':multiple_move,'variants':summarized,'chosen_temperature':chosen,'checkpoint_sha256':digest,'input_sha256':proofs,'active_matching_processes':active,'gpu_compute_processes':gpu.strip(),'both_locks_free':True,'optimizer_steps':0,'new_native_games':0,'limitation':'Archived training rows were sampled by the predecessor7415, not5398. This evaluates5398 probabilities on TRAIN states only, not exact on-policy replay or learning. Temperature does not add missing destinations.'}
    (out/'AUDIT.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
