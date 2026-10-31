"""Prepare a versioned bounded threat release, reusing verified ACK-drain source epoch."""
import difflib,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'strategic-terminal-ack-drain-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OLD/'CANDIDATE_MANIFEST.json').read_text());entries={p:dict(e) for p,e in manifest['files'].items()}
for relative in entries:
    dest=HERE/'candidate'/relative;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_bytes((OLD/'candidate'/relative).read_bytes())
header=HERE/'candidate/AI/DirectorAI/TypedPolicyProtocol.h'
header.write_text(header.read_text()+'''
// Bounded replan predicates use only published visible-state scalars.
#include <cmath>
namespace LabThreatReplan
{
inline bool pressure(int hx,int hy,int hz,double own,int tx,int ty,int tz,double enemy)
{
 if(hz!=tz || !std::isfinite(own) || !std::isfinite(enemy) || own<=0 || enemy<1.5*own) return false;
 const auto dx=static_cast<long long>(hx)-tx,dy=static_cast<long long>(hy)-ty;
 const auto ax=dx<0?-dx:dx,ay=dy<0?-dy:dy;
 return ax<=12 && ay<=12;
}
inline bool allowed(bool enabled,bool hasRetained,bool pressureNow,bool used,unsigned legalMoves)
{ return enabled && hasRetained && pressureNow && !used && legalMoves>1; }
}
''')
h=HERE/'candidate/AI/DirectorAI/CDirectorAI.h';text=h.read_text()
needle='\tmutable std::vector<std::pair<int3, double>> visibleThreats;';assert text.count(needle)==1
text=text.replace(needle,needle+'\n\tbool threatReplanEnabled = false;\n\tmutable std::set<int> threatReplanUsed;')
h.write_text(text)
cpp=HERE/'candidate/AI/DirectorAI/CDirectorAI.cpp';text=cpp.read_text()
needle='\tplayerID = *cb->getPlayerID();';assert text.count(needle)==1
text=text.replace(needle,needle+'''
 const auto * replanMode=std::getenv("LAB_ADV_THREAT_REPLAN");
 const std::string mode=replanMode ? replanMode : "off";
 if(mode!="off" && mode!="once") { typedFailure("invalid_threat_replan_mode");return; }
 threatReplanEnabled=mode=="once";
 logGlobal->info("DirectorThreatReplanMode player=%d mode=%s",playerID.getNum(),mode);
''',1)
needle='committedTargets.clear();recruitedThisTurn.clear();';assert text.count(needle)==1
text=text.replace(needle,'committedTargets.clear();threatReplanUsed.clear();recruitedThisTurn.clear();')
needle='''				const Candidate committed = *retained;
				candidates.assign(1, committed);''';assert text.count(needle)==1
replacement=r'''				const Candidate committed = *retained;
                bool pressureNow=false;int3 trigger(-1,-1,-1);double enemyValue=0,ownValue=0;
                if(threatReplanEnabled && !threatReplanUsed.count(hero->id.getNum()) && candidates.size()>1)
                {
                    ownValue=ArmyDescriptor(hero,true).getStrength();const auto pos=hero->visitablePos();
                    for(const auto & threat:visibleThreats)
                        if(LabThreatReplan::pressure(pos.x,pos.y,pos.z,ownValue,threat.first.x,threat.first.y,threat.first.z,threat.second))
                        { pressureNow=true;trigger=threat.first;enemyValue=threat.second;break; }
                }
                if(LabThreatReplan::allowed(threatReplanEnabled,true,pressureNow,threatReplanUsed.count(hero->id.getNum()),candidates.size()))
                {
                    threatReplanUsed.insert(hero->id.getNum());
                    const auto pos=hero->visitablePos();std::ostringstream record;
                    record << "{\"event\":\"bounded_threat_replan\",\"player\":" << playerID.getNum()
                      << ",\"decision_id\":" << externalDecisionSerial+1 << ",\"own_turn\":" << ownTurns
                      << ",\"day\":" << cb->getCalendar().getCurrentDay() << ",\"hero\":" << hero->id.getNum()
                      << ",\"from\":[" << pos.x << ',' << pos.y << ',' << pos.z << "]"
                      << ",\"previous_goal\":[" << committed.destination.x << ',' << committed.destination.y << ',' << committed.destination.z
                      << "],\"previous_kind\":" << committed.kind << ",\"available_moves\":" << candidates.size()
                      << ",\"own_army_value\":" << ownValue << ",\"threat\":{\"position\":[" << trigger.x << ',' << trigger.y << ',' << trigger.z
                      << "],\"approx_army_value\":" << enemyValue << "}}";
                    logGlobal->info("DirectorThreatReplan %s",record.str());
                    if(const auto * trace=std::getenv("LAB_ADV_TRACE"))
                    { std::ofstream file(std::string(trace)+".replan.jsonl",std::ios::app);file << record.str() << '\n'; }
                }
                else candidates.assign(1, committed);'''
replacement=replacement.replace(r'\t','\t')
text=text.replace(needle,replacement);cpp.write_text(text)
for relative,e in entries.items():e['candidate_sha256']=sha(HERE/'candidate'/relative)
(HERE/'CANDIDATE_MANIFEST.json').write_text(json.dumps(dict(schema='typed-bounded-threat-replan-v2',compiled=False,installed=False,
    plan_sha256=sha(HERE/'PLAN.md'),files=entries,native_games=0,optimizer_steps=0),indent=2))
diff=''
for relative in entries:
    diff+=''.join(difflib.unified_diff((OLD/'candidate'/relative).read_text().splitlines(True),(HERE/'candidate'/relative).read_text().splitlines(True),fromfile='ack-drain/'+relative,tofile='bounded-replan/'+relative))
(HERE/'candidate.diff').write_text(diff)
builder=(OLD/'build_capsule.py').read_text();dest=HERE/'build_capsule.py';assert not dest.exists();dest.write_text(builder)
print(json.dumps({'prepared':True,'files':len(entries),'native_writes':0,'optimizer_steps':0}))
