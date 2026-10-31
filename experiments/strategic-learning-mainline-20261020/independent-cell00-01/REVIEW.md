# 首格独立复核（仅 cell00）

CPU 独立重跑原生只读审核，输出与原 raw-audit/AUDIT.json 完全一致；核对新 pipeline epoch、capsule 源码/工件与冻结输入链、样本准入链和实际 T2 checkpoint。原 CUDA exact replay 证书通过，本文未独立重跑 CUDA。CPU 复算所选动作 logprob 最大误差 4.21e-7。

实际对 EmptyAI 在 day115 胜利，811 个策略决策为 752 次移动、59 次主动结束回合；另有55次无可动英雄自动结束。638个 one-move 状态中59次 stop，平均 stop 概率8.885%；173个 multi-move 状态无 stop，平均 stop 概率0.142%，条件分布仍明显不同。全部主动 stop 时尚有正移动力（最小174、中位810、最大1410），证明真实消耗回合机会，尚不证明学会有效等待。988个我方注册请求与真实ACK匹配。

新训练入口保持原采样、奖励与PPO；新阶段核对 native epoch/编译来源，精确 CUDA 回放和全8格覆盖在更新前关闭准入。虽然单独准入函数主要检验 native epoch，训练入口还要求 collection pipeline epoch 与冻结采集源码一致，未发现首格发生旧入口混用。该结论仅针对当前冻结入口与首格证据。

整批随后在 cell06 因对手原生请求实际 apply=false 被严格拒绝，batch01 最终失败、0 PPO更新，不能用首格证明模型变强或整批成功。历史异seed首格不是配对控制；缺少同预算T1新训练对照，不能将任何轨迹差异归因于温度。

详细计数、逐回合消耗和输入SHA见本目录 AUDIT.json；后续整批失败诊断见 ../independent-batch01-failure-01/。
