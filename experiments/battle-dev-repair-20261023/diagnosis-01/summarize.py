import argparse,json
from pathlib import Path
def main():
    p=argparse.ArgumentParser();p.add_argument('--audit',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=json.loads(a.audit.read_text());assert d['passed'];dev=d['DEV'];output={}
    for opponent in ['BattleAI','MMAI_MODEL']:
        output[opponent]={}
        for arm in ['control','candidate']:
            rows=[x for x in dev['pairs'] if x['arm']==arm and x['opponent']==opponent]
            output[opponent][arm+'_vs_parent']=dict(positive_flips=[dict(map=x['scenario'],role=x['role']) for x in rows if x['win_delta']==1],negative_flips=[dict(map=x['scenario'],role=x['role']) for x in rows if x['win_delta']==-1],shared_losses=[dict(map=x['scenario'],role=x['role']) for x in rows if not x['parent_win'] and not x['candidate_win']],paired_mean_units_lost_delta=sum(x['units_lost_delta'] for x in rows)/len(rows),identical_sequences=sum(x['full_policy_sequence_equal'] for x in rows))
        rows=[x for x in dev['control_vs_candidate_pairs'] if x['opponent']==opponent]
        output[opponent]['candidate_vs_control']=dict(positive_flips=[dict(map=x['scenario'],role=x['role']) for x in rows if x['win_delta']==1],negative_flips=[dict(map=x['scenario'],role=x['role']) for x in rows if x['win_delta']==-1],shared_losses=[dict(map=x['scenario'],role=x['role']) for x in rows if not x['control_win'] and not x['candidate_win']],paired_mean_units_lost_delta=sum(x['units_lost_delta'] for x in rows)/len(rows),identical_sequences=sum(x['full_policy_sequence_equal'] for x in rows))
    a.out.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
if __name__=='__main__':main()
