"""Read-only native review evidence; never starts a game or edits inputs."""
from pathlib import Path
import hashlib,json,sys

OUT=Path('/mnt/g/Heroes3-AI-Lab/experiments/strategic-server-barrier-readonly-audit')
ROOT=Path('/root/heroes3-ai-lab/src/vcmi-adv')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
specs={
 'server/CGameHandler.cpp':[(509,582)],
 'server/CGameHandler.h':[(85,94),(278,290)],
 'server/battles/BattleProcessor.cpp':[(50,61)],
 'server/queries/QueriesProcessor.cpp':[(21,48)],
 'server/queries/BattleQueries.cpp':[(100,112)],
 'server/battles/BattleResultProcessor.cpp':[(426,452),(681,693)],
 'AI/DirectorAI/CDirectorAI.cpp':[(387,395),(476,508)],
 'AI/Nullkiller2/AIGateway.cpp':[(143,151)],
 'client/NetPacksClient.cpp':[(940,945),(970,975)],
}
data={}
for name,spans in specs.items():
 p=ROOT/name; a=p.read_text().splitlines()
 data[name]={'sha256':sha(p),'excerpts':[{ 'start':lo,'end':hi,'text':'\n'.join(f'{i+1}: {a[i]}'for i in range(lo-1,min(hi,len(a))))}for lo,hi in spans]}
p=Path('/root/heroes3-ai-lab/workers/adv-runs/economy-v4-engineering-map0-red-2026101860-2026101860-8l20tn8f/client.log')
a=p.read_text().splitlines()
failure={'file':str(p),'sha256':sha(p),'tail': '\n'.join(f'{i+1}: {a[i]}'for i in range(23920,min(24050,len(a)))),'classification':'spurious_post_battle_action_not_executed','requested':195,'confirmed':194,'request_id':310,'proof':'BattleEnded callback sends new MoveHero at log24002-24004 before PlayerEndsGame consumed24010 onward; no server received/execution proof for310.'}
OUT.mkdir(exist_ok=True)
(OUT/'SOURCE_REVIEW.json').write_text(json.dumps(data,indent=2))
(OUT/'FAILURE04.json').write_text(json.dumps(failure,indent=2))
import torch
(OUT/'START05B.json').write_text(json.dumps({'interpreter':sys.executable,'torch':torch.__version__,'device':'legacy broker CPU; no optimizer or training','failed_initial_launch':'acceptance-05 system python3 missing torch before game/pool','active_run':'acceptance-05b','native_lib_sha256':sha(Path('/root/heroes3-ai-lab/src/vcmi-adv-build/bin/libvcmi.so'))},indent=2))
print('Read-only evidence written')
