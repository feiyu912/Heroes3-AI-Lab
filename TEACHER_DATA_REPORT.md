# 教师数据与质量验收

2026-10-14。当前主数据 `/root/heroes3-ai-lab/datasets/teacher-balanced-v1`，约522MiB，只保留在WSL。36个同兵种、接近兵力且反向部署的军队场景，20训练/6验证/10测试；每场景双侧12场，共864场、20,415决策。仅普通兵堆、无主动施法/随机障碍/攻城/战争机器，包含飞行/双格/部分兵种被动效果，不代表全兵种。

训练480场11,124帧（9,496独立状态）、验证144场3,442帧（3,005）、测试240场5,849帧（5,165）；跨集合精确编码hash交集0。BC明确去重，原始数据保留。WAIT5858、MOVE2639、AMOVE7910、SHOOT4008、DEFEND0。不能把“不防御”当成模型已懂防御：已完成3场强制合法DEFEND后由教师正常打完的协议测试，PPO也实际探索DEFEND，但缺教师监督。

每步NPZ保存全部Observation节点/关系/索引、合法ID及全候选mask，JSON保存真实教师chosen action、语义描述、battle/scenario/seed/episode/side、地图hash、版本和服务器终局。标签来自BattleEvaluator.selectStackAction、原强度计算和原难度搜索步数；没有拿诊断策略作教师。初期hex/unit近战编码错位已用规则解析修复，失败数据保留teacher-v1，不静默删除。

有效采集映射失败0、非法标签0、非有限值0，战斗全部真实正常结束。重复编码发现2个动作冲突组，共6帧（约0.03%）：分别不同移动落点、不同近战落点/目标，全部合法；具体根因尚未确定，可能是编码遗漏或启发式排序，不能断言等价。187组相同观测有不同未来胜负，符合随机未来的可能，也反映编码需要加强。当前去重历史实现取首个标签/结果，已明确记录，后续应保留多标签/估计平均Value；原数据没有删掉。

Action ID仅对应本状态，BC按候选位置建label。Teacher metadata、真实战前兵力和未来终局不能进入Policy输入；仅当前可见v15节点/边进入features。复活/召唤/镜像和完整冒险地图永久保存仍未验收，伤亡数量奖励只用于本无复活课程。

随机对手原回调每次调用random_device，不可复现；已修复实际connector为持久seeded mt19937，使用engine seed+100000。两独立进程轨迹/终局一致。首轮不可复现混合实验排除并保留，已从BC按同预算重新训练，不混入有效结果。

完整质量证据：datasets目录manifest.json、research/teacher-label-audit.json、scenarios-v2.json、random-opponent-replay.json、defend-protocol-probe.json。采集与审计脚本支持12worker、新目录及scenario manifest，不覆盖原训练数据。复杂数据扩展前优先追加逐堆HP/数量/攻防速和显式行动状态。
