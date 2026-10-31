# One-update free-transfer DEV: independent CPU review and observed regression

All16 strict raw auditors were actually rerun and every full AUDIT.json equals the original. All5090 full CPU proposals were recomputed from exact request bytes and the actual833 initialization/6dd updated checkpoint and matched their stored proposals, selected candidates and native bindings. Frozen source/capsule/raw hashes passed. No native/GPU process or optimizer was started by this review. Root's132-step exact GPU restoration and six-negative-case certificate was read, not rerun here.

| DEV arm | Wins | Builds | Income builds | Policy EndTurn | Prewindow transfers |
|---|---:|---:|---:|---:|---:|
|Initialization833|5/8|95|16|0|17|
|Updated6dd|4/8|70|11|0|8|

Pair06 (reserves map, player0, Nullkiller2, fixed seed2026103806) is the sole negative outcome flip. The four successful EmptyAI cases remain successful. These are same-capsule paired games; the isolated qualification fixture is excluded. The updated checkpoint is not promoted. See `review-01/REVIEW.json` for every arm and identical-observation prefix.

Pair06's complete policy requests1–4 are byte-semantically identical. The first different selected action is request4, whose raw SHA is f7cd5bad562ca03312963ec3ebd65af49739fc4c72d99cb9440e7641162f2e92. Both actual CPU argmax decisions replay exactly. Day1 hero2 at[8,12] has army2860,924MP, no visible enemy threat. Own town18[6,8] has army2254. The policy build window is already closed; there are51 real moves plus actual EndTurn. This is a genuine free choice between stocked-town refill and a mine, not a forced committed-only request.

| q4 candidate | Pure prior logit (both) | Initial logit/probability | Updated logit/probability |
|---|---:|---:|---:|
|kind4 own town[6,8],next[8,11]|1.658088|2.005413 /0.111990 (argmax)|1.995197 /0.096081|
|kind2 mine[12,14],next[9,13]|2.047901|1.967391 /0.107812|2.074600 /0.104021 (argmax)|
|actual EndTurn|0|-1.903726 /0.002246|-1.888282 /0.001977|

Both models retain prior_scale32 and identical encoded prior inputs. The mine-vs-town ordering flips through the learned residual. Neither candidate's absolute softmax probability increases: total mass also changes elsewhere, so it would be false to say mine probability simply rose. The full52-candidate prior/logit/probability table is in `PROBABILITY_COMPARISON.json`.

Initial's real q4–q7 route returns to town on day1. Two real transfers move9archer and14pikeman from town into the original20pikeman/10archer hero; q8 observes5114 army and emptied stock. Updated instead pursues the mine and first takes the same original town stock on day4. Thus an early learned decision actually changes refill timing; it is not the old free-stock-window execution omission. After q4, q5 requests already differ. This does not prove q4 alone caused the terminal outcome, nor that all unobserved game/RNG state is identical.

Ordinary commitment remains: source snapshot cpp:248–300 retains an admissible previous target to one move while off mode is active. Q4 contains both alternatives, so that old target was not retained; each chosen return/mine destination then governs the following same-turn single-move requests. On the updated final day32, rescue hire occurs from an actually empty town. Hero33 starts1430 army(10pikeman/5archer), so no existing stock is stranded. Q284 has45 moves and chooses enemy hero[10,15] (visible estimate180), despite other visible enemies estimated33239 at[6,9] and32950 at[19,8]. Q285–290 retain that target; q291 presents44 moves and chooses frontier[18,14],next[10,15], with1430 army and empty own-town stock. Actual terminal has no hero/town. Initial eventually wins day131 with army258457 and four own towns. This long divergent history, including initial rescue hires on days26/88 versus updated16/23/32, prevents attributing the whole result to one move.

To check whether q4 is an isolated anecdote, both actual models were evaluated on all2089 immutable admitted TRAIN observations, with the existing encoder/model and no gradients. Group statistics are per observed row, not new native results or PPO weights:

| Original TRAIN group | Rows with both own-town kind4 and mine kind2 | Town argmax initial→updated | Mean town probability initial→updated | Mean town share within town+mine |
|---|---:|---:|---:|---:|
|EmptyAI|228|68→58|0.056070→0.047856|0.431396→0.405828|
|Nullkiller2|18|10→7|0.104470→0.090129|0.431691→0.405873|

Across all2089 observations, town argmax247→229:10 town→mine changes (7Empty/3NK),5 town→build,3 town→other move, with no reverse changes into town. On all1738Empty rows, mean own-town probability0.048511→0.046703; on351NK rows,0.032116→0.030771. This supports a narrower finding: this update reduced refill selection on these observed requests, including genuine NK choices. The18-row NK subset is small; these are states collected by the initial policy and do not measure the updated policy's new state distribution or universal behavior.

All four original NK TRAIN episodes have terminal loss, all four EmptyAI episodes win. The row-count imbalance is not itself a PPO weighting claim: the unchanged training algorithm balances episodes. There is no successful NK Training trajectory in this batch to directly reinforce, whereas the separate reserves DEV initial policy can win. That demonstrates a gap in observed successful experience across conditions; it does not prove sparse credit assignment or map distribution is the sole root cause. No reward, native candidate, initialization or teacher target was changed, and DEV q4 is not used as an expert training label.

`PAIR06_EVIDENCE.json` retains exact public requests, responses, own-state logistics and raw-bound terminal events. It reads no hidden enemy armies, saves or map objects. `PROBABILITY_COMPARISON.json` binds original samples and both model SHA values and preserves per-row inferences. These diagnosis/review tools are separate nested analysis artifacts and are not retroactively claimed as training protocol sources.
