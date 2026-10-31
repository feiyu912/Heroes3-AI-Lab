# WAIT-bait v1：训练阶段否决

新 train/dev/test 划分在运行前冻结。实际只跑 train：2图×双角色×2种子×teacher/wait-bait，共16局全部正常原生终局、无非法/截断，完整终局事件均保存。

8个配对单元：主力 swordsman 平均少损0.125、总永久损失平均少0.125，但净胜-1。4次真实 WAIT 覆盖；严格“诱饵先触发目标 COUNTER→同回合主力非致死攻击且不再被反击”机制10例，teacher6例。因此是机制增加却收益失败，没有通过预设门槛，不看 development/test，不生成BC，不晋升模型。

初版分析跳过整个跨round批次，曾给出机制0/0；但严格 START/FINISH 内我方请求动作的round可确定为前决策round，后续对手动作才使返回批次跨round。修正离线分析后为10/6，原raw未改，终局配对结果不受影响。旧保守分析可用 --round-mode same-batch 重现，保留于 PAIRED_RESULTS_CONSERVATIVE.json；新版 PAIRED_RESULTS.json 明确 analysis_version。不能把完整批次中任意事件都归入round_before。

低价值友军活着并不保证本轮可到同一目标。v2 改为从已有图的其它单位假设动作和行动次序关系检查这一必要条件。该变化在新目录冻结，v1 代码/数据保留。

详见 PAIRED_RESULTS.json 与 runs/train 下16组 summary/json.gz/SHA。3篇实际访问的公开文字来源及此处工程复现边界见 ../../adventure-takeover-v5/expert-source-retaliation.json；没有真人轨迹，也不因来源存在自动获得Q3。
