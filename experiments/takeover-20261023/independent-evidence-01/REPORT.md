# 接管证据独立核验

已完整读取 NEW_CHAT_HANDOFF_20261023.md 及索引的战略、战斗、恢复、暂停和清理报告。13 份原始结构证据已记录字节 SHA；29 项当前程序/模型/source 身份检查全部通过，722 项历史证书直接 input_sha256 绑定实际重新逐字节核验通过。清理前后保护列表完全相同，当前受保护 17 个程序/模型 SHA 均匹配。未重演历史 GPU 恢复、原生对局或网络 proposal 重算，不将已读旧证书说成本次复跑。

战略原始独立 REVIEW 仍为同 capsule 初始化 5/8 → 更新 4/8；PAIR06 只有 q4 首次自由动作不同，后续状态分叉；PROBABILITY_COMPARISON 的 2089 TRAIN 观察支持观察集补兵倾向下降，不能证明该单步导致终局失败。战斗 authoritative actual-review-02 为 BattleAI 12/16 → 12/16、作者 MMAI 11/16 → 10/16；480 固定状态仅 12 argmax 改变，不能说没有梯度。240 格全部有正常终局，critic 主导/KL 阻断/难格完全没反馈都不作为已证根因。control60 与 candidate57 两条完整恢复分支不能相加；预定 96 DEV 当时未跑。

原 native-v2 的 9 个 candidate、manifest、contract 和 driver 均与交接绑定匹配，source-ready 不能当实际资格。root 随后隔离修复缺少 GameLibrary.h 的编译问题并生成 v3/capsule02；独立审计原始 mechanism-20261023-01 已通过，最终权威证书为 mechanism-final-02/AUDIT.json。实际17决策、2次招募、4次免费转兵，原生全局 request/ACK/drain、全部七资源、所有 stock level/offer、目的军队和 visitor、真实 whole-stack 转移均由原始字段独立重算。实际首回合 Build → Recruit1 → Move → 同物种 Recruit1 → End；资源 pickup 后英雄实际仍在入口，未捏造回城。catalog SHA 031d9200e3efa40e2dd82363547d6f39e8f1381296f000d8b83b158ca663eb1e，实际库路径/字节绑定 v3 capsule02。13 个实际状态篡改负例均拒绝；原输入未改。机制脚本没有学习能力或胜率意义。

mechanism-actual-01 因日志对 ui8 what 实际输出控制字节导致审计器解析 KeyError；02 修正实际字节解析后通过。后续 final-01 与 final-02 分别加强响应与 runtime/source 绑定并实际重审。中间产物保留，使用 final-02，不掩盖审计演进。

可复用 audit_game(raw,native,mechanism=False) 已交 policy agent，并以最终 auditor SHA 69f3999387e41cf89b8eef0ac22bba95d7bb9018f8355db8154e26fab0cf1188 冻结。每局证明字段按实际事件检查，零 recruit/transfer 的合格局明确计数为0，不证明学会招募。后续完整策略/PPO、保存/加载及配对评估仍须实跑。

TRAIN 信用分配另以独立标准库实现重算，与 root 诊断一致：NK 11 个已选回城全部 stock/hero>=0.5 且 normalized advantage 负；每局 actor 目标质量1/8，不能用行数比例推断梯度失衡。详见 TRAIN_CREDIT_REPORT.md。所有本审计器工作均0新增native/GPU/optimizer，root的新机制运行另行归属。
