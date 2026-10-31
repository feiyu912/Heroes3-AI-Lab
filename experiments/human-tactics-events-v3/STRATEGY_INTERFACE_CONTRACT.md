# 战略侧接入边界 v3.1

提供：单场合法动作执行、审计事件的正确时间关联、稳定单位 ID 的已知/未知身份、完整原生终局和永久伤亡；提供离线既有夹具 runner。当前没有胜率估计、校准损失预测器、已认证专家、有效新模型。

raw value 不得当作概率；未知预测返回 null。动作内伤害不是长期净收益，有限反击机制的验证也不是战略战斗可胜保证。

冒险 ML-off 运行时与这里复用的 ML-on events-v2 运行时不可混用二进制或动态库。当前 runner 没有接收冒险对局任意真实战斗状态的桥；不能新开独立夹具后宣称是在预测当前战斗。

数据：json.gz 中 initial_observation、batches、transitions、stable_identity、retaliation_audit。batches 只交付一次，batch_id 单调，caused_by_step 指明哪个请求引发，最后一步返回批次包含 BATTLE_END。每个 transition 记录合法动作、实际 action、前后图、pre/post batch ID、严格 native action window。

Q2-event-correspondence 只说明选中行动确实发出了对应攻击；所有当前样本 eligible_for_bc=false、certified_expert=false。独立/未使用测试状态必须从实验用途判断，不能只看旧 manifest 的 split 名字。
