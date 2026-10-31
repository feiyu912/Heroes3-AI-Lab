# User-requested pause — 2026-10-20

The user explicitly requested stopping and a phase conclusion. Do not restart any learner, game, compilation or implementation without a later resume instruction. The full goal is unfinished.

## Actual shutdown

Interrupted economy_policy, threat_design_review and multihero_supply. Sent SIGINT only to the identified candidate learner PID10056 for battle-continuation-lr-paired-01. Its existing KeyboardInterrupt path closed native workers; controller session17790 exited1, preserving evidence. This is a user pause, not a game loss or a spontaneously failed model. No timeout/partial game becomes a training outcome.

Actual post-stop /proc and nvidia-smi inspection found no lab native game, learner or controller, and no GPU compute application. Both GPU learner and pool locks were acquired nonblocking and released, proving availability. Evidence: experiments/battle-training-continuation-20261020/monitor-independent-01/user-pause-01/PAUSE.json.

## Last completed battle states

- Parent30 had3840 actual Adam calls. Control completed30 additional updates/15360 rows/3840 new Adam; global60 cumulative7680. SHA443863dd26ea0daaed17cd01ab3dd44a6a16544efac73c96a89839f5b72c0e20.
- Candidate completed27 additional updates/13824 rows/3456 new Adam; global57 cumulative7296. SHA8d3169e85d51b0bf7d7247cc2d4bdc6949410d5262793f1729a6463dbd3976bf. The unfinished next rollout is not a completed update.
- Latest full models were copied to the G workspace user-pause-01 directory and byte SHA verified. Original Linux checkpoints, rollouts and reports remain intact. These are two separate optimizer branches; do not add their counters into one chain.
- The planned96 DEV games did NOT run. Therefore the learning-rate comparison has no final strength verdict. Do not blindly relaunch its controller: that controller starts both arms from fixed parent30 and would redo completed work. A later resume needs an explicit remaining schedule and strict loader qualification. Native in-flight state was not saved/restored.
- Earlier completed60-map training genuinely performed30 updates/3840 Adam/15360 rows. Its64 DEV showed BattleAI12/16→12/16 and public MMAI11/16→10/16; no promotion. These small fixed DEV samples do not replace historical population-rate evidence.

## Strategic results and real limits

Actual schema5 learned building and complete native-game collection work. The exploration chain completed4 same-optimizer updates/504 Adam/8012 rows/130 real policy builds, including6 income buildings; final paired DEV4/8→4/8, no gain.

The free-town-stock execution flaw was reproduced and repaired in capsule02. Actual native fixture proved new hire10 pikemen→receive existing20 pikemen and10 archers before first policy decision; resource/army conservation and real ACKs were verified. This fixture was mechanism-only, never PPO or a strength score.

After that repair, the fresh original eight TRAIN cells yielded2089 rows/41 real policy builds (3 income)/4 wins4 losses and132 actual CUDA Adam calls. Model6dd26e29b55364c293d9874c36a743e4636bcd0208daf5e61042e1f8b506ea00 passed real full learner CUDA boundary recovery. Fixed16DEV was5/8→4/8, no promotion. Independent16raw+5090 CPU proposals passed exact review. The negative pair first diverged at identical observation q4: baseline returned for reinforcements, trained model chose a mine. TRAIN comparison also showed reduced reinforcement preference; this does not prove a single action caused the final loss.

Complete strategic evidence archive:29317 files/108 symlinks/733736527 bytes, verified twice; manifest SHA13a2f96e7f7a9bb80cef040c3361a588b092998610296320184e9e55b8cc2ef9 in strategic-learned-free-transfer-run-v1/independent-dev-01/delivery-01. External Data/Mods link targets were preserved, not falsely reported as copied trees.

## Unfinished recruitment work

strategic-learned-recruitment-native-v1 is the preserved draft. Reviewed v2 removes only its init execution gate; manifest865988a27bc8de8f257b767ac5b10927e76da96fe974e37414fe7519f38e7830, contract1f3a9d3c0777e31787df5e8cd2a2af1614d326a04f9b0f85ac0e83c3e42d15a3. Source includes native recruit availability/quantity choice, actual tuple binding, full stock/army/resource ACK checks, same-species new-stock transfers, and runtime creature catalog export. It is NOT C++ compiled or game-qualified.

The new policy encoder/model is CPU-only draft with synthetic-state projection/gradient checks, not a trained recruitment model. Real runtime creature catalog, new capsule, schema6 mechanism qualification and fresh PPO remain undone. New run/policy hooks were being prepared when interrupted; any partial files remain unqualified. Do not enable flags merely because a draft/static check passed.

Current strategic learner is still single-hero, recruitment in the qualified running version is scripted, and native BattleAI handles whole-game battles. The independently trained graph battle model has not been integrated into that controller. Human tactics still have no qualified positive-benefit expert course; withdrawn labels must not be used. The95% BattleAI/stable MMAI targets and full strategic generalization remain unmet.

On a later authorized resume, read this file and current processes first. Preserve all frozen source/runtime evidence and one-GPU/pool-lock rules. Continue actual strategic recruitment qualification/training alongside the remaining bounded battle comparison; do not make local battle95% a prerequisite for strategy development.
