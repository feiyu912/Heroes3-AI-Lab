# Heroes III AI Research Lab：技术可行性报告

调查日期：2026-10-13（北京时间）。范围：技术调查、架构设计、轻量诊断；未开始正式 AI 开发、完整引擎编译或训练，未修改 F:\heroes3。

**后续运行验证更新：** 按用户后续要求，已在独立WSL2副本完成训练引擎/Gym构建及15场真实战斗回归，状态、合法动作、reset、固定种子独立进程重播和正常退出通过。随后补充服务器战前兵力及伤亡接口，完成1/2/4/8环境并行实测：固定无魔法弓箭手场景中，4环境约500次决策/秒，8环境约811次决策/秒、采样总PSS约2.35GiB。原报告中“未构建/运行/测量”为调查阶段历史状态；最新结果及适用范围见 [实测报告](research/BENCHMARK_RESULTS.md) 和 [环境状态](research/ENVIRONMENT_STATUS.md)。尚未启动模型训练。

## 先回答十个关键问题

| 问题 | 结论与证据边界 |
|---|---|
| 一张 5070 Ti 能否训练有竞争力的战斗 AI？ | **具备训练小型战斗决策网络的资源条件；竞争力尚待实验。** 16GB 显存无需承担语言生成模型；本机 sm_120 CUDA 极小计算已成功。魔法组合、泛化和评价质量比参数规模更关键。不能承诺击败高手。 |
| 14700KF + 32GB 是否足够初期多环境 RL？ | **足够开展受控的初期实验，合理起点 2–4 个战斗进程。** 8–12 个仅是有条件的扩容候选；28 逻辑线程不等于 28 环境。实际 RSS、重置和搜索开销尚未测量。 |
| 当前 vcmi-gym 能否直接复用？ | **值得复用，但不能直接接到当前本地 upstream 源码。** Gym 固定训练 fork，要求 libmlclient；本地 MMAI v13，Gym 同时含 v13/v15。先锁定匹配版本，补构建、种子验证、采样与评测；主动魔法和战略接口另行扩展。 |
| 最值得选择的 Decision Model？ | **共享实体编码 + 动态候选动作评分 + 可选 Value Head**；先做轻量集合/注意力编码。把 v15 小型异构 GNN 作为同预算对照，不默认大型 Graph Transformer。 |
| RL 必要吗，何时开始？ | **不是必要条件。** 先测启发式、搜索、BC、搜索蒸馏；接口可靠且教师上限明显时，在 Stage A 后半段进行小预算 Masked PPO 对照。 |
| PPO、模仿还是蒸馏？ | **组合且有门槛：BC 打通链路 → 搜索蒸馏提高教师 → 可选 PPO 改进 → 对手池。** 如果搜索收益更大且延迟合格，可长期保留传统搜索。 |
| 大地图和战斗是否分开训练？ | **应分开。** 时间尺度、可见信息、动作和奖励不同；以战后永久战损、法力和战略任务接口连接。 |
| 中期能否主要依靠本地？ | **能开展并迭代中期战斗项目。** 完整魔法覆盖与竞争力没有实测保证；先降低数据/图规模，而非租大 GPU。 |
| 最终 1 VS 7 最大瓶颈？ | **推断：部分可观测战略规划、跨天经济/接力/防守、七方联盟资源优势和有效评测数据。** GPU 大小未必是首要瓶颈；该规则下并非所有地图都可赢。 |
| 第一次编码从哪里开始？ | **一个固定小战斗的 reset → 可见状态/合法动作 → 确定性规则策略 → step → 终局统计 → 种子回放。** 在匹配训练 fork 上验证；随后接小模型评分。无需先训练或重构整个 VCMI。 |

## 证据等级与复核入口

- **[事实/本机]**：本次命令或本地源码直接验证；代码存在不等于运行成功。
- **[事实/源码]**：固定提交的公开源码可定位；尚未在本机编译运行。
- **[作者报告]**：维护者文档/实验叙述，未经本机独立复现。
- **[推断]**：由已知规则或工程约束推导的建议。
- **[估计]**：带假设的实验起始值，不能作性能承诺。
- **[未知]**：未运行或缺少公开证据。

固定提交、论文及代码入口见 [研究来源与证据索引](research/SOURCES.md)。保留的远程源码节选和 API 快照位于 research/evidence；未下载游戏资产或模型权重。源码调查并非全仓逐行审计。

## 1. 本机与游戏资产

**[事实/本机]** G:\Heroes3-AI-Lab\vcmi 是干净的源码工作区，HEAD `0883081b31dc97f326075f7b0326abaa8161b18e`，提交日期 2026-10-13，origin 为官方 vcmi/vcmi。包含 BattleAI、Nullkiller2、MMAI。此次没有发现已配置的本项目训练运行结果，也没有执行构建。

CPU 为 i7-14700KF，系统报告 20 核、28 逻辑处理器；物理 RAM 34,163,888,128 字节（约 31.82GiB）；Windows 11 Pro。NVIDIA-SMI 报告 RTX 5070 Ti、16,303MiB 显存、610.88 驱动，诊断时桌面等约占 1,128MiB。GPU 不空闲到可以把全部显存算给训练。

Windows Python 3.13.5，现有 PyTorch `2.10.0.dev20251107+cu128`，CUDA runtime 12.8，包含 sm_120；32×32 CUDA 矩阵计算结果正确（32768）。这只证明基本可执行，不证明 GNN 扩展、ONNX GPU、训练稳定性或吞吐。未发现 Windows 当前 Python 环境中的 gymnasium、onnxruntime。

WSL2 Ubuntu-22.04 可启动，内核 6.6.87.2；CMake 3.22.1、G++ 11.4、Python 3.10.12 已存在，WSL NVIDIA-SMI 能识别 GPU。未验证 WSL PyTorch。WSL 报 localhost 代理未镜像的提示，后续依赖下载网络需单独验证。当前本地 MMAI CMake 要求 3.24，WSL 的现有 CMake 对启用该模块不足；升级工具是后续构建工作，不是已完成事实。

**[事实/本机]** F:\heroes3 存在 Heroes3.exe、HD Mod DLL、Data 中的 LOD/SND/VID 资源。目录也存在 HotA 命名文件/模板，这只证明安装包含相关组件，不证明用户正在使用 HotA。研究按用户指定 Complete + HD Mod、无 HotA；未来 VCMI 内容清单需明确禁用额外模组，资源导入使用独立数据目录。

Heroes3.exe 大小 2,826,240 字节，SHA256 `55de13886018c220b6f2fa3106f9c620cb7f682b47bb73cfe82064d8b501cdbe`。它与 homm3-decomp 固定的 2,732,032 字节、SHA256 `057c9d88e7206f6669a4615de2c6e02ab6c4e2d570a9e2badf07fe0bd6247274` 不一致。**不能把该仓库的函数地址直接映射到本机 EXE**，也不能仅凭差异判定游戏版本或修改原因。

## 2. 四个参考项目的实际状态

| 项目 | 本次固定版本 | 能利用什么 | 不能推出什么 |
|---|---|---|---|
| VCMI 官方 | 本地 `0883081…` | 精确规则、AI callbacks、BattleAI/Nullkiller2、MMAI ONNX 接入、保存框架 | 不等于原版 NWC AI，也不等于已有 Gym 战略训练 API |
| vcmi-gym | `11241d496db95541766498373e23245a67847a97`，2026-10-13 | 战斗 Gym、v13/v15 编码、PPO/GNN、双侧对手与向量化代码 | README 明示安装文档过时，不能声称一键构建可用 |
| 训练引擎 fork | Gym gitlink `e956242503f465ae6ec0a62a3aeb2c4ea179db5c` | ML/、server/ML/、libmlclient、v15 schema | 与最新官方 ABI/目录布局兼容未知，不能随意换成主干 |
| REA | `cae7620b77ec2893c944197603cc9158e2224930`，2026-10-13 | 本地原生程序分析的工具协调和证据记录 | 不自动恢复原始源码；Windows/Ghidra 能力需按实际 provider 验证 |
| homm3-decomp | `da7baf0d61025fd3f31f47dad48dbcc876a86917`，2026-10-12 | Complete 固定二进制的匹配重建，src/philai.cpp 可辅助理解原始 AI | README 的匹配比例是项目报告，不是本机验证；当前构建不是可玩的完整替代引擎 |

[事实/源码] 三个指定远程项目当天或近期有提交；没有把星标量当维护质量指标。README、分支和运行接口不同步时，以固定源码为准。REA 暂未安装/启动，没有进行深度二进制分析。原版 AI 逆向作为辅助专项研究，不作为训练环境的前置条件。

**补充发现**：[vcmi-gym Issue #5](https://github.com/smanolloff/vcmi-gym/issues/5) 发布了战略层分支。核查 `c18593395/vcmi-strategic-gym` 的 `be284df…` README：它声明 3464 维状态、25 动作，需要 companion vcmi-native 引擎，训练 harness 位于另一个 workspace，公开 CI 主要做 Python 语法检查。这属于有价值的接口参考，不能据公告视为完整可复现实验或八人地图成熟方案。上游维护者在该 issue 提出了许可/来源声明问题；后续复用时应核实其是否已解决。此处不作法律结论。

## 3. vcmi-gym / MMAI 能力核查矩阵

| 调查项 | 当前证据 | 结论及缺口 |
|---|---|---|
| 从源码编译 | connectors CMake 查找 `mlclient`，训练 fork 定义该共享库；pybind11 为 gitlink | [源码]构建路径存在；[未知]本机编译通过。SSH 子模块地址、路径预设、依赖和 ABI 必须处理 |
| Windows 原生 | VCMI 本身有 Windows 构建；Gym 无 Windows 安装指南，connector 有 SO 风格路径/后缀处理 | Windows VCMI 可作为目标；Gym 原生 Windows 不作为已验证训练方案 |
| WSL2 | Linux 训练路径存在；本机 WSL 工具/GPU 已识别 | [推断]优先 WSL2；仍需依赖、文件系统、C++ 扩展 smoke test |
| 无图形模拟 | 官方 clientapp/EntryPoint.cpp 有 headless；训练 MLClient 设置 headless/onlyai | [源码]支持无 GUI 路径；没有实测是否所有初始化都无图形/音频依赖，更没有“快速”的数字 |
| 多环境 | PyConnector 对每进程第二个独立 VCMI 实例明确报错；dual vec env 使用 multiprocessing | 独立环境采用多进程；同一战斗双方双接口可共享 connector，不是两个独立模拟器 |
| observation | 本地 v13 固定编码；训练 v15 为 Global/Player/Unit/Hex/Action 五类节点和关系边 | v15 有动态图与 active_action_ids；具体尺寸由 exporter 导出，不硬写旧文档尺寸 |
| action | v13 2 + 165×14 = 2312 固定输出；v15 动态 Action 节点，Python 声明 Discrete(9999) 容器 | v15 真正合法集合由当步 active IDs 决定；9999 不等于应输出9999个 logits。需验证上限行为 |
| 全部主动魔法 | v15 ActionType 只有 WAIT/DEFEND/MOVE/AMOVE/SHOOT；v13 maybeCastSpell 调 BattleEvaluator，训练 v15 同样有传统施法路径 | **模型不能直接学习任意主动魔法选择。** 添加施法时点、英雄/法术/法力/目标关系和动作协议 |
| 英雄/技能 | 环境可随机 heroes、primary skills、mana；Unit 含有效能力/状态 | 配置能影响规则不等于 observation 含完整英雄状态；没有完整技能学习/升级动作接口证据 |
| 墙/障碍/攻城 | town_chance/random_obstacles/warmachine；v15 编码 wall health、gate、bridge、stopping/damaging hex | [源码]已有表征，不能宣称尚未实现；[未知]所有攻城规则与样本覆盖正确 |
| 召唤/镜像 | v15 Unit 中 IS_CLONED/IS_SUMMONED 注释掉，注明当前训练不出现 | 引擎规则存在与训练表征是两回事；Stage B 需来源、临时单位与持久价值区分 |
| 完整大地图 | 上游 Gym step/reset 为战斗；训练 fork 有完整引擎作为载体 | **上游不是现成完整对局 RL 接口。** 需新增战略可见状态、宏动作、问答/升级、日/周推进和胜利接口 |
| 序列化/恢复 | 官方 CGameState/BattleInfo 存在 serialize；Gym connector 可 reset/replay 战斗 | 不等于 Python 可任意 clone/restore 全状态；搜索还需 RNG、事件/回调、临时状态恢复验证 |
| 固定随机种子 | constructor seed 传到 fork server/ML；reset(seed) 只调 Gym seed，connector.reset 未传 seed | **不能把每次 reset(seed) 视为引擎重播。** 独立进程从同 seed 启动并核查轨迹；必要时扩接口 |
| PPO/GNN/自对弈 | rl/v15/ppo_gnn.py、gnn_model.py（GENConv 默认）；OTHER_ENV、双侧向量化代码 | 可复用算法/批处理思想；不能宣称已复现权重效果，v15 不兼容本地 v13 factory |
| 最适合扩展处 | schema/exporter、Action 节点、connector、对手池、评测器 | 先保持训练 fork 独立，再把可审查的适配移回官方；不要覆盖现有源码 |

维护者日志报告 v15 采用动态图、共享 PPO actor/critic 来降显存，并混入保护射手的脚本对手和自身模型；这支持“批量与对手多样性很关键”的研究方向，**不提供本机吞吐或人类胜率证据**。[维护者日志](https://smanolloff.github.io/projects/vcmi-gym/)

## 4. 现有传统 AI 已有什么

[事实/本地源码] BattleAI 包含攻击/威胁/交换模拟与法术目标评估，而非只会贪婪攻击。`getSimulationTurnsCount` 在 difficulty < 4 返回 2，否则 10；MMAI 传统施法使用固定 2 回合。应记录完整混合策略的成本。

SpellTargetsEvaluator 对单目标类型进行枚举，对位置法术有筛选；目标类型数量 != 1 有未支持多 destination 的分支。这是瞬移等多参数法术的研究入口，不能据此推断整个引擎没有该法术。

Nullkiller2 已有英雄链、Dimension Door、Town Portal、飞行路径状态、经济/探索/目标行为与威胁分析。学习器应优先替换排序/风险估值模块，保留规则与规划。源码中 openMap 与 object graph 受 cheatsAllowed 和队伍人类条件约束；配置默认 openMap false，但只看一个字段不足以证明公平性。正式比赛同时关闭 cheatsAllowed 并审计 callback 可见信息。

## 5. 从高手战术到可检验任务

已知策略不能全部压成“造成伤害”。双格喷吐含友军误伤与攻击朝向，尸巫云雾受目标种类和邻接影响，九头怪多目标受占位影响；这些应由规则层给出候选影响集合。等待改变后续速度序列，骗反击/保护射手需要跨行动评价。失明、复活、镜像、瞬移、力场涉及施法时点、持续状态及未来可达性。

额外研究任务：[推断/待规则验证] 等待后跨轮双动、快兵风筝与弹药耗尽、无反击/攻击返回配合、驱散对增益和控制的取舍、反魔法与免疫、压制法术和反制准备、牺牲/复活的永久与临时恢复差别、撤退/投降的经济选择、战术布阵、主英雄保留机动法力、周初补兵与攻城时间窗、侦察诱导与威胁下的资源取舍。不要默认 VCMI 与原版对每项交互完全一致。

## 6. 可行性边界与决策

**[推断]初期主要风险是接口与数据质量，中期是环境/搜索吞吐和内存，远期是战略归因与评测。** 小型结构化网络可用本地 GPU；16GB 不能自动承载现有 v15 的全部默认图缓存和多模型训练。

支持进入下一轮受控实现，但本阶段停止在文档与诊断。下一轮开始前先完成版本选择、一个 reset/step smoke test、持久战损统计和可重复性，再决定是否增加神经网络。没有运行条件的指标保持未知。实验预算、架构、奖励与推进门槛分别见其余六份文档。
