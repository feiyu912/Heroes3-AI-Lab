# Human pilot 空关系维度恢复

原60步BC在尚未执行梯度更新前失败：JSON将空edge attrs的(0,width)形状写成[]，旧unpack恢复成一维(0,)，与二维非空关系混批np.concatenate不兼容。原失败control、bc-training.log及全部源数据保持原位并另作逐字节副本。

本恢复不修改human-tactics-v1任何已有Python。`run_pilot.py`、`train_bc.py`为隔离派生版本；场景、24局、未来模型和独立评估结果仍放原v1数据目录。调用原冻结`run_episode.py`生成未来测试；其输出同样经严格身份/哈希/原生终局核验。

使用expert-knowledge-v1/graph_observation_codec.py，以实际NODE_TYPES/EDGE_TYPES的size恢复所有节点/边矩阵，包括空关系，并校验边索引与合法动作ID。先完成CPU预检，才允许根任务排GPU。

实际CPU预检覆盖24局718条决策、2471个空关系；所有维度和索引通过。固定24局清单中6个正常获胜专家局产生185条Q2候选，双方角色均有样本；使用真实B64模型按8条混批独立CPU编码并按16条计算有限交叉熵。没有启动游戏或GPU。完整证据见cpu-preflight.json与recovery-manifest.json。

## 运行入口

根任务统一安排资源后运行：

```bash
bash /mnt/g/Heroes3-AI-Lab/research/run-lab.sh /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-recovery-v2/run_pilot.py
```

该入口不重跑24局收集，只在同一全局池锁下运行60步GPU policy-head BC，然后冻结并跑原先固定的12条件×2模型独立战术测试。原failed pilot-control.json不改，当前控制状态和新日志在本v2目录。旧模型、旧报告或不兼容产物绝不覆盖；BC报告/模型半成品如存在则停止调查。

完成后只读复核：

```bash
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/expert-knowledge-v1/audit_human_pilot.py --control /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-recovery-v2/pilot-control.json
```

CPU预检可用同run-lab环境执行check_recovery.py；它仅加载schema与CPU模型，不启动模拟器。recovery-manifest关联所有原始脚本、failed control/log、24局报告/gzip、场景清单SHA以及恢复代码/codec版本。启动时严格复核，代码改动后必须重做CPU预检。

## 恢复加强项

- 按固定24局manifest选源，逐局核scenario/role/policy/seed/split、checkpoint当前SHA、地图和脚本冻结SHA、gzipSHA、内外记录、合法动作及原生胜负，不使用glob旧重复文件。
- BC复用必须匹配原始权重SHA、输出模型SHA、60步、精确source_episodes、样本数与恢复代码哈希。
- 未知/非正常结算的战损不当0纳入均值，报告有效分母与unknown_final_losses。旧24局全正常，未触发历史零值问题。
- Q2仅探索性标签拟合。即使训练损失下降，也不证明专家最优、战术学会、反制有效或普通战斗提升；真人轨迹/Q3与PPO对照仍需后续证据。
