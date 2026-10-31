"""Counterfactual numerical objective analysis only; never relabels/adopts a game."""
import copy,json
from pathlib import Path
import torch
from load_admitted import load
from episode_balanced_ppo import prepare_batch
HERE=Path(__file__).resolve().parent
rows,_,_=load(HERE/'admitted-episode-01')
counterfactual=copy.deepcopy(rows)
for r in counterfactual:r['return']=-r['return']
# No episode manifest: these counterfactual labels are NOT certified training data.
a=prepare_batch(rows);b=prepare_batch(counterfactual)
assert not a['metadata']['collector_manifest_verified'] and not b['metadata']['collector_manifest_verified']
delta=float((a['advantages']-b['advantages']).abs().max());assert delta<1e-5
out=HERE/'single-episode-centering-analysis-01';out.mkdir(exist_ok=False)
result=dict(passed=True,analysis_only=True,native_outcome_unchanged=True,counterfactual_samples_admitted=0,optimizer_steps=0,
    float32_normalized_advantage_max_difference=delta,
    algebra='For one constant-terminal-return episode: (R-V)-mean(R-V)=mean(V)-V. Centering removes R from the actor advantage; critic still receives R.',
    consequence='Single-episode update is engineering qualification only. Use fresh same-policy multicell episodes with mixed terminal outcomes before drawing learning conclusions.',
    excluded='Do not combine the initial-parent win with a later-parent loss; that would be off-policy.')
(out/'AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
