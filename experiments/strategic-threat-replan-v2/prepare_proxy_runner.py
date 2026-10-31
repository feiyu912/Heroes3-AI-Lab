"""Add explicit scripted evaluation arm; preserve all executed source versions."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;TRAIN=HERE.parent/'strategic-typed-training-v1'
text=(TRAIN/'evaluation_broker.py').read_text()
text=text.replace('from pathlib import Path',"from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path(__file__).resolve().parent.parent/'strategic-typed-training-v1'))\nfrom clearance_proxy import choose as choose_clearance\nfrom live_jsonl import read as read_jsonl",1)
text=text.replace('def __init__(self, mode, checkpoint=None, diagnostic_action=None):',
    'def __init__(self, mode, checkpoint=None, diagnostic_action=None, agent_dir=None, proxy_enabled=False):\n        self.agent_dir,self.proxy_enabled=agent_dir,proxy_enabled',1)
needle='        response = dict(schema=RESPONSE_SCHEMA';assert text.count(needle)==1
text=text.replace(needle,"""        recommended=index
        explanation=dict(index=index,overridden=False,method='frozen_model_argmax',reason='proxy_disabled')
        if self.proxy_enabled:
            events=read_jsonl(self.agent_dir.parent/'strategy-trace.jsonl.replan.jsonl')
            matches=[e for e in events if e['decision_id']==request['request_id']]
            assert len(matches)<=1
            explanation=choose_clearance(request,index,matches[0] if matches else None)
            index=explanation['index']
"""+needle,1)
needle='model_sha256=self.model_sha256,value=value,execution_verified=False,';assert text.count(needle)==1
text=text.replace(needle,'model_sha256=self.model_sha256,value=value,execution_verified=False,\n                    model_recommended_index=recommended,clearance_proxy_enabled=self.proxy_enabled,proxy=explanation,',1)
needle="    parser.add_argument('--max-requests'";assert text.count(needle)==1
text=text.replace(needle,"    parser.add_argument('--clearance-proxy',action='store_true')\n"+needle,1)
text=text.replace('broker=Broker(args.mode,args.checkpoint,args.diagnostic_action)',
    'broker=Broker(args.mode,args.checkpoint,args.diagnostic_action,args.agent_dir,args.clearance_proxy)',1)
text=text.replace("mode=args.mode,model_sha256=broker.model_sha256,device='cpu',optimizer_steps=0)",
    "mode=args.mode,model_sha256=broker.model_sha256,device='cpu',optimizer_steps=0,clearance_proxy_enabled=args.clearance_proxy)",1)
outputs={'clearance_broker.py':text}
text=(HERE/'run_game.py').read_text()
text=text.replace("BROKER=HERE/'evaluation_broker.py'","BROKER=Path(__file__).resolve().parent/'clearance_broker.py'",1)
text=text.replace('threat_replan=args.threat_replan,load_save=', 'threat_replan=args.threat_replan,decision_policy=args.decision_policy,load_save=',1)
text=text.replace("inputs=[Path(__file__),HERE/'live_jsonl.py',source", "inputs=[Path(__file__),Path(__file__).with_name('clearance_proxy.py'),Path(__file__).with_name('PROXY_PLAN.md'),HERE/'live_jsonl.py',source",1)
needle="'--idle-seconds',str(args.seconds+30)],stdout=blog";assert text.count(needle)==1
text=text.replace(needle,"'--idle-seconds',str(args.seconds+30)]+(['--clearance-proxy'] if args.decision_policy=='clearance' else []),stdout=blog",1)
needle="            assert ready['mode']=='new-policy'";assert text.count(needle)==1
text=text.replace(needle,"            assert ready['clearance_proxy_enabled']==(args.decision_policy=='clearance')\n"+needle,1)
needle="    p.add_argument('--threat-replan'";assert text.count(needle)==1
text=text.replace(needle,"    p.add_argument('--decision-policy',choices=['model','clearance'],required=True)\n"+needle,1)
outputs['run_proxy_game.py']=text
for name,text in outputs.items():
    p=HERE/name;assert not p.exists();compile(text,str(p),'exec');p.write_text(text)
(HERE/'PROXY_RUNNER_MANIFEST.json').write_text(json.dumps(dict(files={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in outputs},
    optimizer_steps=0,native_games=0,meaning='Scripted evaluation branch with recorded frozen-model recommendation; never an expert or PPO sampler'),indent=2))
