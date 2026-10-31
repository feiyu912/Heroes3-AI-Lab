# 真实BattleAI教师数据

日期：2026-10-14。12个环境并行采集，数据在 `/root/heroes3-ai-lab/datasets/teacher-v2`，体积约81MiB，不放入Git。

- 12个多兵种、无魔法场景，攻守两侧，每组20场：480场、3219决策。
- 按Scenario ID分为8个训练场景、2个验证场景、2个测试场景；同场战斗和同场景两侧不跨集合。
- 训练2007帧/320场、验证501帧/80场、测试711帧/80场。
- 精确独立状态数分别728、229、243。跨集合完整节点/边状态hash交集均0；集合内有大量重复，不能把3219帧当成3219个独立局面。
- WAIT1140、MOVE796、AMOVE859、SHOOT424、DEFEND0。防御监督缺失，是当前数据局限；PPO可合法探索防御，不代表已学会合理防御。
- 完成数据中映射失败0、非法标签0、非正常终局0、截断0。每个数组检查有限值，mask/候选/标签匹配。

教师实际调用训练fork的BattleEvaluator.selectStackAction，复用BattleAI原有getStrengthRatio和按难度选搜索步数的函数。没有用诊断策略生成教师标签。当前教师是无主动魔法/撤退/战争机器条件下的BattleAI兵堆行动选择，不冒充全功能教师。

首次采集失败保留在 `/root/heroes3-ai-lab/datasets/teacher-v1`。原因是近战目标分别以hex和unit编码。修复通过BattleAction.getTarget和battleGetUnitByPos解析，比较起步格、目标兵堆和返回位置，不猜伤害规则。当前课程不含龙喷吐/尸巫范围攻击；不能把“同一目标兵堆”扩大解释为所有特殊攻击的等价行动。修复后的数据另存teacher-v2，未覆盖失败证据。

每场保存NPZ完整Observation（节点、关系和索引）、合法ID、全候选mask，JSON保存Chosen Action、可读引擎动作、Battle ID、Scenario ID、引擎构造seed、episode序号、双方、地图hash、teacher版本、终局结果和schema。Action ID只在对应状态内有效，不当作跨状态固定标签。训练按候选位置取label。真实战前军队/终局结果和教师标签仅作为元数据或监督目标，绝不作为模型输入。

同一进程reset继续引擎随机序列；构造seed和episode序号共同定义轨迹。独立模型对战测试为每场新进程、同构造seed配对，避免宣称reset(seed)已重置引擎。

证据：research/teacher-quality-v1.json、scenarios-v1.json。完整源补丁为research/lab-v2-native.patch（含此前终局与目录隔离改动），搭配原兼容补丁并重新构建engine/connector。旧runtime-manifest.json保持历史证据，新版本使用runtime-manifest-v2.json。

复跑：先make-training-maps.py；然后teacher-pipeline.py --workers 12 --episodes 20 --dataset <新的目录>，脚本拒绝覆盖已有数据。后续优先补防御/障碍课程、更多场景、训练集去重和多个引擎seed；不把重复极小场景当作成熟教师数据。
