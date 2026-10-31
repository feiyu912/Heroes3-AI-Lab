# 混合专家 Reference PPO：准备态

2026-10-16。当前仅完成隔离实现与CPU预检，**未启动CUDA、游戏或训练，未冻结可执行最终方案**。draft-plan.json的finalized_for_execution=false，训练器会拒绝执行该草案。root须结合当前32更新开发和专项结果确定初始化、参考与预算后，另外显式冻结最终plan。

## 已实现

- 每phase精确24worker：12普通BattleAI（6进攻/6防守）、8脚本专家MMAI_GPU/OTHER_ENV传输（4/4）、4原生公开MMAI_MODEL（2/2）。每16更新换phase，场景和种子预生成；32更新对应两phase。配置比是50%/33.33%/16.67%，不是50/30/20；日志另报每类别/角色实际decisions、正常终局、胜负和截断。
- 专家进一步按family×role分层：龙喷吐、死亡云、单兵诱饵各至少1进攻+1防守；额外一对角色随phase轮换family。当前phase0死亡云2/2、其余各1/1；phase1龙2/2、其余各1/1。CPU与运行门禁都检查该覆盖，避免总4/4却遗漏龙课程。
- 普通/历史只用diverse-curriculum的train；专家只用Human v1的12张train图。地图SHA、来源清单、neutral hero、原生/环境/代码和公开ONNX冻结。实际worker默认loose阵型，tight默认0、random_primary_skills默认0；lab-env明确随机障碍0、法力0，不宣称复现tight布局或任意hex。
- 支线commit 5e3a7152d3ea8d3cc4626f4802480c3e50ac1fbf的ExpertOpponent仅作Q2弱脚本对手。冻结bootstrap/opponents以及实际LEGACY coverage依赖SHA，用自己的源门禁与策略配置检查，不信任其恒True的assert_unchanged。safe_multi只作覆盖代理，包含喷吐/死亡云，不称认证战术成功。
- 单独冻结reference pair，默认公开initial-pair。与learner不共享参数/optimizer；reference逐步从同一raw obs独立encode，合法候选完整分布KL。历史原生ONNX始终是原公开MMAI，不随reference改变。
- 复用已验reference_ppo.py的GAE、PPO、合法KL与24批量重算，atol2e-4/rtol0。deterministic CUDA；默认public起点，lr1e-5、gamma1、stepcost0、shaping0.5、entropy0.005、KL0.1、rollout32、32updates。仅policy/value heads更新。
- controller独占共享flock并将真实锁FD传给trainer；trainer拒绝缺锁或草案。16/32保存优化器、Torch CPU/CUDA、Python/NumPy RNG、准确heads模式与计数。resume只接受本方法、相同planSHA/完整config的16更新边界checkpoint；不会加载B64旧全参数优化器。环境按冻结下一phase重启，不声称恢复未存的局内引擎状态。
- rotation/finish关闭worker前，逐env统计“已采样但尚未正常终局/环境截断”的ongoing fragments。term/trunc后该env步数归零；关闭摘要记录片段数、已采样步数和category/role。它们已进入bootstrap训练但没有完整终局，单独报告，不算胜负、环境truncation或假奖励；checkpoint包含累计关闭记录。

## CPU已执行证据

check_mixed.py在真实训练图观测上检查24个专家合法动作、真实图编码/heads前后向、有限梯度、reference/body不变、源SHA错误拒绝。每phase类别/角色与三个family×role计数正确，train-only，英雄零属性/无主动魔法和worker规则已查。旧logp按24重算误差0。合成片段计数检查覆盖term/trunc清零、rotation两片段、finish一片段，未改变终局/奖励。结果见cpu-preflight.json；没有保存训练候选，CPU一次数学更新不构成游戏训练收益。

最早随机专家草案漏掉phase0龙课程，后经root检查修为上述分层；随后加入片段透明统计。旧draft/旧CPU结果分别保存在before-family-stratification和before-fragment-accounting文件中，旧源快照也保留；均未执行游戏训练，不能把修复前证据当当前方案通过。

## 操作入口（本次未执行训练）

草案和CPU检查：

```bash
bash /mnt/g/Heroes3-AI-Lab/research/run-lab.sh /mnt/g/Heroes3-AI-Lab/experiments/expert-mixed-ppo-v1/check_mixed.py
```

root决定最终起点后另建计划。例如保持默认公开起点/参考：

```bash
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/expert-mixed-ppo-v1/run_experiment.py --freeze-plan
bash /mnt/g/Heroes3-AI-Lab/research/run-lab.sh /mnt/g/Heroes3-AI-Lab/experiments/expert-mixed-ppo-v1/check_mixed.py --plan /mnt/g/Heroes3-AI-Lab/experiments/expert-mixed-ppo-v1/experiment-plan.json
```

随后只能由root统一排程明确`run_experiment.py --run --plan ...`。freeze操作本身不训练；final plan须通过同一精确SHA的CPU预检才可--run。

新方案可显式传`--checkpoint B64_PATH`和独立`--reference-checkpoint B64_PATH`，默认仍都是公开模型；应另选`--plan`新文件名，不能覆写已有初始化。只改初始不自动改reference，只改reference不改历史ONNX。文件内学习率、固定32预算等冻结后不能暗换；未来预算改变需扩phase并复验新版本。

恢复时在同一plan下显式`--resume-checkpoint .../update-16.pt`；只在原参数/版本一致时加载本方法优化器。旧partial训练报告先备份，不覆盖不相干模型或报表。刚开始尚未保存16更新时没有本方法可恢复点，应保留失败日志并由root决定重新从冻结初始权重开始。

## 尚未证明

没有24worker实际boot/吞吐、CUDA真实重算/续训、专家反制收益、普通能力保留或新独立胜率。CPU合法性只覆盖24个真实状态，不保证脚本是强专家；强制多目标优先会产生已知偏差。没有从任何BC权重自动初始化，也未纳入四条混杂WAIT示范。此路线同时改经验分布与策略约束，不是单变量归因实验。

正式执行后应先检查boot、原生终局、各类实际采样和冻结参考，再完成48开发场景双对手回归与等预算消融，冻结候选后另跑未读确认集。原已读512只作失败诊断，不能冒充新独立测试。
