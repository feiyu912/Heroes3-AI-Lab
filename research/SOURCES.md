# 研究来源与复核索引

调查日期2026-10-13。源码以固定SHA为准；作者叙述、issue和文档是辅助证据，不等价于本机实验。research/evidence中保存了本次API元数据与选定源码文本。完整Git tree元数据不等于下载完整仓库。

## 固定源码入口

- [本地对应官方VCMI提交](https://github.com/vcmi/vcmi/tree/0883081b31dc97f326075f7b0326abaa8161b18e)
- [BattleAI难度/交换模拟入口](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/AI/BattleAI/BattleAI.cpp)；[法术目标枚举](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/AI/BattleAI/SpellTargetsEvaluator.cpp)
- [本地MMAI v13施法路径](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/AI/MMAI/BAI/v13/BAI.cpp)；[factory版本与ONNX](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/AI/MMAI/BAI/factory.cpp)；[v13动作类型](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/AI/MMAI/schema/v13/types.h)
- [Nullkiller2路径/英雄链目录](https://github.com/vcmi/vcmi/tree/0883081b31dc97f326075f7b0326abaa8161b18e/AI/Nullkiller2/Pathfinding)；[信息/作弊条件](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/AI/Nullkiller2/Engine/Nullkiller.cpp)；[难度配置](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/config/ai/nk2ai/nk2ai-settings.json)
- [headless入口](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/clientapp/EntryPoint.cpp)；[CGameState保存接口](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/lib/gameState/CGameState.h)
- [Gym固定版本](https://github.com/smanolloff/vcmi-gym/tree/11241d496db95541766498373e23245a67847a97)；[README安装状态](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/README.md)
- [Gym v15环境/reset/action/配置](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/vcmi_gym/envs/v15/vcmi_env.py)；[每进程单VCMI约束](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/vcmi_gym/envs/v15/pyconnector.py)；[connector构建](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/vcmi_gym/connectors/CMakeLists.txt)
- [v15 GNN网络](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/rl/v15/gnn_model.py)；[v15 PPO](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/rl/v15/ppo_gnn.py)；[双侧/向量化](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/rl/algos/mppo_dna_gnn/dual_vec_env.py)
- [Gym锁定训练引擎](https://github.com/smanolloff/vcmi/tree/e956242503f465ae6ec0a62a3aeb2c4ea179db5c)；[ML库构建](https://github.com/smanolloff/vcmi/blob/e956242503f465ae6ec0a62a3aeb2c4ea179db5c/ML/CMakeLists.txt)；[v15动作枚举](https://github.com/smanolloff/vcmi/blob/e956242503f465ae6ec0a62a3aeb2c4ea179db5c/AI/MMAI/schema/v15/types.h)；[v15图观测与临时单位缺口](https://github.com/smanolloff/vcmi/blob/e956242503f465ae6ec0a62a3aeb2c4ea179db5c/AI/MMAI/schema/v15/graph.h)
- [REA固定版本](https://github.com/morluto/rea/tree/cae7620b77ec2893c944197603cc9158e2224930)；[README/provider要求](https://github.com/morluto/rea/blob/cae7620b77ec2893c944197603cc9158e2224930/README.md)
- [homm3-decomp固定版本](https://github.com/sushi-shi/homm3-decomp/tree/da7baf0d61025fd3f31f47dad48dbcc876a86917)；[固定EXE/hash](https://github.com/sushi-shi/homm3-decomp/blob/da7baf0d61025fd3f31f47dad48dbcc876a86917/config/project.toml)；[原始AI重建philai](https://github.com/sushi-shi/homm3-decomp/blob/da7baf0d61025fd3f31f47dad48dbcc876a86917/src/philai.cpp)

## 维护者报告与当前问题

- [MMAI研究日志](https://smanolloff.github.io/projects/vcmi-gym/)：v15动态图、显存优化、对手多样性，作者报告，非本机复现；未采用其宣传性表现作胜率结论。
- [Gym issue列表](https://github.com/smanolloff/vcmi-gym/issues)：本次API中open #3构建错误、#5战略分支公告；#3年代久，不当作当前全部构建失败证据。
- [战略分支公告与维护者反馈](https://github.com/smanolloff/vcmi-gym/issues/5)；[战略分支固定README](https://github.com/c18593395/vcmi-strategic-gym/blob/be284df2b5361797f3b9f6e7d53e826e75c0c08d/README.md)
- [VCMI #7806 超大军队战斗结束崩溃](https://github.com/vcmi/vcmi/issues/7806)，API当日closed；[VCMI #7792 战术技能](https://github.com/vcmi/vcmi/issues/7792)，closed；[VCMI #7971 回合耗时/限制](https://github.com/vcmi/vcmi/issues/7971)，open。标题/状态是调查线索，不能由状态推断运行效果。

## 算法原始资料与软件文档

- [PPO，Schulman等，2017](https://arxiv.org/abs/1707.06347)：策略更新基线；不提供H3样本复杂度。
- [Invalid Action Masking，Huang/Ontañón](https://arxiv.org/abs/2006.14171)：合法集合上的policy gradient；掩码不是学习规则的替代。
- [SB3-Contrib MaskablePPO官方文档](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_mask.html)：向量评测/mask接口；动态候选图需适配，不能直接假设标准固定Discrete配置足够。
- [Potential shaping，Ng/Harada/Russell，1999](https://ai.stanford.edu/~ang/papers/shaping-icml99.pdf)：折扣潜势差的条件，不用于证明任意启发式奖励安全。
- [AlphaZero，2017](https://arxiv.org/abs/1712.01815)、[MuZero，2019](https://arxiv.org/abs/1911.08265)：Policy/Value/搜索协同与学习动力学；不转用其他游戏训练指标。
- [Graph Attention Networks](https://arxiv.org/abs/1710.10903)、[GATv2](https://arxiv.org/abs/2105.14491)：图注意力结构依据；H3收益待实验。
- [Options，Sutton/Precup/Singh，1999](https://www.cs.swarthmore.edu/~meeden/DevelopmentalRobotics/suttonOptions.pdf)：可变时长宏动作与SMDP。
- [POMCP，Silver/Veness，2010](https://proceedings.neurips.cc/paper/2010/hash/edfbe1afcf9246bb0d40eb4d8027d90f-Abstract.html)：基于信念采样的规划。
- [NFSP，Heinrich/Silver，2016](https://arxiv.org/abs/1603.01121)：不完全信息自对弈；不声称八人联盟收敛。
- [IMPALA，2018](https://arxiv.org/abs/1802.01561)：异步actor/learner与策略滞后；本机先不引入分布式复杂度。
- [PyTorch 2.7 Blackwell支持](https://pytorch.org/blog/pytorch-2-7/)；[NVIDIA CUDA/WSL指南](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)；[Microsoft WSL CUDA](https://learn.microsoft.com/windows/ai/directml/gpu-cuda-in-wsl)。软件版本兼容最终以本机smoke和依赖检查为准。

## 本机证据与边界

GPU计算结果见 [torch-smoke.json](evidence/torch-smoke.json)，机器/目录摘要见 [local-diagnostic.json](evidence/local-diagnostic.json)，证据文件hash见 [manifest.json](evidence/manifest.json)。API快照包含gym/rea/decomp提交日期、分支和tree；training-fork-tree保存Gym gitlink树。raw来源均用固定commit。一次尝试读取REA `docs/providers/ghidra.md`返回404，未据此得出Ghidra不存在的结论；REA概览依据实际README。VCMI #7971网页本次返回404，但搜索API返回该issue元数据，故仅将标题作调查线索。

本次未编译引擎、跑环境或读取全部论文全文；论文采用原始摘要/已知算法定义及公开入口，具体H3适配为工程推断。文档中的吞吐/训练效果都保持未知；资源数值注明理论算例或假设预算。
