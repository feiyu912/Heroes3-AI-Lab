# 论文可行性评估 · 增量复核（2026-10-23）

**本文件定位**：工作区中存在另一会话产出的 `PAPER_FEASIBILITY_20261023.md`（下称"原评估"）。本文件**不覆盖、不替代**它，只补三件原评估缺失或需要修正的事：

1. **先行工作与新颖性边界的外部核查**（原评估 §6 写"arXiv 全库检索 *Heroes of Might and Magic* 命中 0 篇"——**这一条经 arXiv API 复核属实**，`all:VCMI` 亦为 0 命中；但"没有直接竞品"的说法**不准确**：arXiv 之外的学术与非学术先行工作至少有三条，必须正面引用）；
2. **一个 P0 级工程阻塞项**（原评估列为 G7"不可一键复现"，实际比这更严重：整个研究代码**不在任何版本控制之下**）；
3. **许可与合规红线**（上游作者刚刚因 Apache-2.0 合规问题公开发过 issue，这直接关系到能不能把代码作为 artifact 附在论文上）。

另附：与我方独立审计的资产清单、投稿窗口的已核实日期，以及一份统一优先级清单。

本文件只做判断与规划，不启动训练、不修改实验输入。

---

## 0. 总判断（与原评估一致的部分先说清楚）

**能写，但写不了"我们更强"那篇。** 冻结 512 局终测：选定模型 84.8% vs BattleAI（上游公开模型 89.3%）、52.3% vs 上游 MMAI（场景聚类 95% 为 44.1–60.5%，下界低于 50%）。战略层 8 次独立配对评估**零提升**（4/8→4/8、5/8→4/8、6/8→6/8、四臂 32 局全 4/8）。

原评估提出的 P1（winner's curse）/ P2（角色不对称 + 信用跨度）/ P3（基准发布）/ P4（战略层暂缓）**选题判断我全部认同**，下面只做补强与一处修正。

---

## 1. 修正一：先行工作核查（这一条会改变论文的写法）

原评估 §6 写"arXiv 全库检索 *Heroes of Might and Magic* 命中 0 篇……没有直接竞品"。**这个说法需要修正**，至少有三条必须正面引用的先行工作：

### 1.1 已发表的学术先行工作（2015）

> Wilisowski, Drezewski 等（AGH University of Kraków），*The Application of Co-Evolutionary Genetic Programming and TD(1) Reinforcement Learning in Large-Scale Strategy Game VCMI*，**KESAMSTA 2015**（Springer CCIS；DBLP `conf/kesamsta/WilisowskiD15`）。
> https://home.agh.edu.pl/~drezew/papers/drezewski2015application-coevolutionary.pdf

**含义**：把"VCMI 当作大规模策略 RL 研究载体"这件事本身**不是新的**，2015 年就有人做过（GP + TD(1)，非深度 RL）。因此论文**不能**写"首次将 H3 用于 RL 研究"这类表述；能写的只是"**在现代深度 RL + 真实引擎原生集成 + 审计级评测**下的新结论"。这一条不修正，投稿时会被直接命中。

> 补充核实（2026-10-23，arXiv 官方 API）：`all:"Heroes of Might and Magic"` → **totalResults 0**；`all:VCMI` → **totalResults 0**。即**arXiv 上确实没有 H3/VCMI 相关论文**，原评估这句话本身没错——但"没有直接竞品"只在 arXiv 范围内成立，上述学术论文与公开 issue 都在 arXiv 之外，审稿人做 related work 时同样会挖到。

### 1.2 一个已公开宣布、且现已删除的战略层竞争实现（必须引用）

`vcmi-gym` issue #5（2026-09-30，作者 c18593395）公开宣布了一个**战略层（adventure）**的 RL fork：

- 自博弈 PPO，**约 350 万训练步**，带针对内置 AI 的 win/loss 门控；
- 观测 = **3464 维状态 + 4×21×21 地形通道**，**25 个战略动作**；
- 发布 ONNX `bc_model_v3464b.onnx`（release `v3.0-strategic`）。

**2026-10-23 核查结果**：该仓库与其 releases 现均返回 **404（已删除）**，该 GitHub 账号下仅剩 `rea` 与 `vcmi` 两个 fork，**权重已不可下载**。
**含义**：
- "首个完整对局 H3 强化学习"这一表述**不可用**（有公开在案的先行实现）；只能写"首个**可审计、可复现、保留阴性结果**的完整对局 RL 智能体"。
- 反过来，这块**当前公开可得的竞争实现为零**，是真实空窗。

### 1.3 上游作者的公开许可争议（关系到 artifact 能不能发）

同一 issue 下，vcmi-gym 作者于 2026-10-05 公开指出：上述 fork 大量包含 vcmi-gym 的 **Apache-2.0** 代码，却以 MIT 名义发布、未附 Apache 许可副本、未标注修改声明，违反 Apache-2.0 §4(a)(b)。

**对本项目的直接含义**：
- 我们的训练/评测代码确实复用了 vcmi-gym 的 Apache-2.0 片段（`research/evidence/vcmi-gym/` 有源码快照）；
- **若要把代码作为论文 artifact 公开，必须保留 Apache-2.0 许可全文 + 修改声明 + 来源标注**；
- 同时这也是**与上游建立联系的自然契机**：一封邮件说明"以贵方公开权重为起点、遵循 Apache-2.0、附完整许可"，是消除新颖性风险最便宜的一步。

### 1.4 方法论背书（把"只报负结果"变成主张）

> Castro, *The Formalism-Implementation Gap in Reinforcement Learning Research*, arXiv:2510.16175（2025）。
> 主张：RL 研究应从"证明能力"转向"理解学习动力学"，并批评基准与底层形式化脱节。

这篇**可以直接当作线 B/P2 的动机引用**——它为"把审计、协议、负结果当贡献"提供了学术依据，而不是让审稿人觉得"没有性能提升 = 没贡献"。

### 1.5 related work 必须锚定的通用基准（防止"你不是第一个"被质疑）

以下工作**已经吃掉了**你不能声称的贡献点，写作时必须主动区分：

| 工作 | 吃掉了什么 | 你的区分点 |
|---|---|---|
| NetHack Learning Environment（arXiv 2006.13760，NeurIPS D&B 2021） | "程序化生成 + 大规模 RL 基准 + 泛化评测" | NLE 是终端 roguelike；**真实商业引擎 + 原生机制/存档/经济系统**是它没有的 |
| Procgen（ICLR 2020） | 小样本泛化与课程 | 同上 |
| Melting Pot（2023）、SMACv2（NeurIPS D&B 2023） | 多智能体基准、评测套件标准化 | 同上 |
| Cicero（Science 2022，Diplomacy） | "大规模自博弈 + 战略级 AI" | 你没有 Cicero 的规模，**不能比规模**；只能比"真实引擎 + 可审计" |
| MicroRTS（2018）、Lux AI（2023） | 回合制实时策略基准 | **最容易被拿来对比的一类**：它们是简化模拟器；H3 是完整商业规则（含英雄系统、城镇经济、主动魔法），机制复杂度与状态空间性质不同 |
| Gran Turismo Sophy（2023） | "真实物理引擎 + RL + 评测协议" | **最危险的类比**：Sophy 也做真实引擎级 RL。必须明确区分：Sophy 面向驾驶，本工作面向回合制策略 + 合法动作掩码 + 角色不对称 + 长时序信用 |

**写作建议**：不要用"这个游戏很经典/很古老"立论，而要用**回合制战术战斗的独有性质**立论——超大离散合法动作空间、攻守角色不对称（实测 defender 净退 22 胜）、长时序稀疏终局信用（19–24% 行在 phase 内看不到终局）、规则密集（免疫/反击/溅射/召唤）。

---

## 2. 修正二：P0 阻塞——研究代码不在版本控制之下

这是比原评估 G7 更基础的一层问题：

| 事实 | 影响 |
|---|---|
| `G:\Heroes3-AI-Lab` **不是 git 仓库**（无 `.git`，只有一个 159 B 的 `.gitignore`，且排除 `models/`、`*.pt`、`*.onnx`、`*.npz`） | 无法引用版本、无法 diff、无法开源、无法被第三方复现 |
| 全树唯一的 `.git` 是**上游 VCMI**（`vcmi/.git`，develop @ `0883081b3`，工作区干净；本项目仅 1 个本地提交 `5e3a7152d`，在另一个 worktree） | 本项目自己的代码基本处于"未受控"状态 |
| `research/` 约 127 个 .py **平铺、无包结构、无 `requirements.txt`/`pyproject.toml`/`Dockerfile`/根 README** | 第三方拿到仓库也不知道从哪个脚本开始 |
| **真正可执行的真身在 WSL** `/root/heroes3-ai-lab`（约 4.1 GiB），G 盘只有快照与副本 | "发布代码"= 发布另一套东西 |
| `experiments/battle-diverse-curriculum-20261020/final-independent-01/RESUME_READINESS.md` 明确：`native_environment_restorable=false`，CLI resume 曾被门禁拒绝且遗漏 Python/NumPy RNG 与累计 optimizer 计数 | **"一键复现"目前不成立**，D&B / CoG 都会查这一项 |

**建议做法（一天内可完成，且解锁后续一切）**：

1. `git init` 两个仓库：
   - `h3-ai-lab-protocol`：训练/评测/审计代码 + 文档 + 环境脚本（建议 Apache-2.0，与 vcmi-gym 一致）。
   - `h3-ai-lab-evidence`：实验清单、`REPORT/REVIEW/AUDIT` 索引、模型 SHA 清单、协议文档（**只放元数据与索引，不放 13.47 GB 原始数据与 6.79 GB 权重**）。
2. 修 `.gitignore`：权重与大数据改用 **Git LFS 或 release 附件 + SHA 清单**（论文引用的是 SHA，不是文件本身）。
3. 写根 `README.md`（含"从哪条命令开始"）、`requirements.txt`、`LICENSE`、`CITATION.cff`。
4. 许可声明三件套写进 README：VCMI = GPL-3.0 系；vcmi-gym = Apache-2.0（衍生代码保留许可与修改声明）；**不分发任何原版 HoMM3 资源**。

---

## 3. 修正三：许可与合规红线表（投稿前必须处理）

| 组件 | 许可 | 本项目用法 | 论文/发布要求 |
|---|---|---|---|
| VCMI 引擎 | GPL-3.0 系（上游 `vcmi/license.txt`） | 战略层基于源码 fork 改造（`src/vcmi-adv`），战斗层使用 vcmi-gym 的训练 fork | 派生补丁/二进制按 GPL 发布；论文声明不重新分发游戏资源 |
| vcmi-gym | **Apache-2.0** | 战斗层来源、v15 schema、PPO/GNN 参考实现（快照在 `research/evidence/vcmi-gym/`） | 衍生文件须保留许可全文、修改声明、来源标注 |
| MMAI 公开权重 | 随 vcmi-gym release（Apache-2.0 仓库） | attacker/defender 各 19,255,061 B，SHA 已冻结 | 引用 + 标 SHA + 注明"起点为公开权重，非从零原创" |
| 原版 HoMM3 资源（`F:\heroes3`） | 受版权保护 | 仅本地用于 LOD 提取 | **绝不随论文/仓库分发**；写明获取方式与"未包含受版权保护素材" |

**论文措辞红线**：必须写清"战斗主线自公开上游权重继续训练，非从零训练"（你自己的 `research/CHALLENGE_RESULTS.json` 与 `CHALLENGE_RESULTS.md:34` 已如此声明，论文里要保持一致），否则一旦被审稿人核对就会被认为隐瞒起点。

---

## 4. 对原评估的补强（三个我认为可以再往前推一步的地方）

### 4.1 P1（winner's curse）——认同，且可立即执行、零算力

原评估给的方案（重采样模拟 + ICC + dev→test 膨胀量）**完全正确**，补充两点执行细节：

- 13 个候选的 dev 集是 **12 场景 × 双角色 × 2 种子 = 48 局**，场景聚类后有效样本远小于 48；**候选之间共用同一套场景**，所以候选间差异是配对的，应做 **paired bootstrap（按场景重采样，候选成对同抽）**，而不是把每个候选独立重采样。
- 建议再加一个**交叉验证式的对照**：把 13 个候选按 dev 排序做 **Spearman 相关**（dev 排名 vs test 排名），以及"选 dev 第 1 名 vs 选 dev 中位排名"两条线的期望 test 表现差——这比单纯报膨胀量更有说服力。
- 数据全在 `research/CHALLENGE_RESULTS.json` / `research/fresh-challenge-results.json` / `research/challenge-final-selection.json`，**不需要跑任何新对局**，1–2 天可出全部数字。

### 4.2 P2 的"正对照"（原评估 G2）——这是最关键的一条，认同并给两个正对照

原评估指出：审稿人默认"你的 PPO 实现有 bug"，所以需要**弱先验跑同一 PPO 流程**。同意。除 BC-MLP（26.9%）外，还有第二个现成正对照：

> **你自己的"从零训练小模型"三种子结果**：47.5% / 53.125% / 65.0%，均值 55.21%（两层 bootstrap 95% 42.29–71.25%，`research/GOAL_RESULTS.json`）。
> 这条链路的起点是**随机/启发式**，不依赖任何强先验，且已经证明"同一套 PPO + 掩码 + 势函数奖励的实现能把 1.25%（random）拉到 55%"。

把这两条并列（**弱先验 PPO 提升** + **从零训练提升**），就能堵住"实现有问题"的最大质疑；再用**强先验 PPO 净退化**做对照，三段式就完整了：
`从零训练：1.25% → 55%` ⟶ `弱先验 PPO：? → ?` ⟶ `强先验 PPO：84.8% → 84.8%（净退化）`。

> 顺带一个学术包装：这个现象与"强先验 + 窄分布更新导致可塑性下降"高度一致，可接 primacy bias（Nikishin et al., 2022）与 plasticity loss（Dohare et al., *Nature* 2024）文献，把负结果接到已有理论脉络上，而不是孤立的"没涨"。

### 4.3 战略层：同意暂不成文，但留一条"可成文"的底线

战略层当前唯一合格版本是"单英雄神经策略 + 脚本化招募 + 原生免费转兵 + 战斗委托原生 BattleAI"，8 次独立评估零提升，**不能**写成能力主张。但它沉淀了三条**方法论级**结论，若将来要成文，只能以它们为主张：

1. **机制资格化（mechanism qualification）**范式：一个游戏机制必须通过"原生事件 + 资源/库存/军队守恒 + 负例拒绝"才允许进入 PPO 样本；
2. **原生 ACK 不可信**：引擎在 handler 失败时仍可能返回成功码，因此"ACK 通过"不能作为执行证明（这对任何"引擎级 RL"都有用）；
3. **阴性诊断方法**：优势值符号分解（11 个被采样的 NK 回城动作归一化 advantage 全负、均值 −1.099）+ 行为变化量化（回城 argmax 247→229、招募 greedy 0→664→240）+ 奖励塑形对照（两臂 argmax 差异 0、KL 1.87e−8）。

---

## 5. 资产 → 论文材料映射（补充版）

| 论文需要 | 现有文件/资产 |
|---|---|
| 环境与引擎版本 | `research/ENVIRONMENT_STATUS.md`、`research/runtime-manifest-v4.json`、`research/evaluation-provenance-runtime-contract.json` |
| 终测集定义与审计 | `research/challenge-holdout.json`、`research/challenge-holdout-audit.json`（32 套零重复、镜像、审计 passed） |
| 冻结与模型选择 | `research/final-policy-freeze.json`（含 `"final_test_read": false`）、`research/goal_selection.py` |
| 主结果 | `research/CHALLENGE_RESULTS.json`、`research/fresh-challenge-results.json`、`CHALLENGE_RESULTS.md` |
| 溯源校验器 | `research/evaluation_provenance.py`（记录地图、so、onnxruntime、Python 脚本、模型、每张图 SHA 并断言一致） |
| 独立审计器 | **约 140 个**实验级 `audit*.py` + 5 个 project 级审计器（**建议合并为 canonical 包**） |
| 归档与完整性 | `ARCHIVE_MANIFEST.json`（29,317 文件 / 733.7 MB / 全量重算 SHA）、`evidence-package-01/ARCHIVE_VERIFIED.json`（688 文件 / 5.44 GB） |
| 学习动力学 | `LEARNING_MAGNITUDE.json`、`experiments/battle-train-credit-20261023/REPORT.md`（27,648 行 GAE 独立重算，误差 2.4e−7）、家族课程梯度拆分 REVIEW（critic/actor = .32/.13/.05/.05） |
| 战略机制资格 | `experiments/strategic-learned-recruitment-native-v3/qualification/PLAN.md`、`strategic-multihero-supply-native-v1/CARGO_V3_INDEPENDENT_REVIEW.md` |
| 负例/拒绝集 | `experiments/*/AUDIT.json` **916 份**；失败批次保留；`DATA_QUALITY_WITHDRAWAL.json`（62 条 Q3 撤销） |
| 图表 | 仅 `research/plot-challenge-results.py`、`plot-goal-results.py` + 4 张图；**experiments/ 下 0 张图、0 条学习曲线、0 个 tensorboard** |
| 文献索引 | `research/SOURCES.md`（17 条）→ 需扩到 60+ 条并并入 §1 的先行工作 |

**规模**：`experiments/` 103 个实验目录、13.47 GB、273,708 文件；`REPORT.md` 30、`AUDIT.json` **916**、`REVIEW.md` 23、`MANIFEST*` 23；`.pt` 398 个 / 6.79 GB。

---

## 6. 投稿窗口（已核实日期，标注来源；其余以官网为准）

| 目标 | 日期 | 核实情况 | 适配 |
|---|---|---|---|
| arXiv cs.LG / cs.GA | 随时 | — | **高**：先占位，抢"审计级 H3 评测"的话语权 |
| **AAAI 2027** | 投稿 **2026-07-21**（会议 2027-02-16） | myhuiban 会议库 | 低（已过；AAAI 2028 可期） |
| **IJCAI 2027** | 投稿 **2027-01-04**（会议 2027-08-07） | myhuiban 会议库 | 低（单游戏 + 负结果，主 track 不友好） |
| **AIIDE 2026** | 投稿 2026-06-19（已过），开会 2026-11-09，Belo Horizonte | myhuiban 会议库 | AIIDE 2027 预计约 2027-06 |
| **ICLR 2027** | 摘要 2026-09-18 / 正文 2026-09-25（**均已过**），决定 2026-12-16 | 官网 CFP | 低；ICLR 2028 可期 |
| **IEEE CoG 2027** | 会期 **2027-09-01 ~ 09-04**，西班牙马德里 Complutense 大学（CoG 2026 同址同期；截稿按惯例约 2027 年 1–3 月，**待官网确认**） | 会议目录站 | **高**（游戏 AI 正会，认方法学 + 阴性结果） |
| **FDG 2027** | 约 2026 年末–2027 初（**待官网确认**） | 未核实 | 中高（偏研究方法与设计，契合） |
| **NeurIPS 2027 D&B** | 约 2027-05（**待官网确认**） | 未核实 | 中（需 P3 级打包，单游戏窄是硬伤） |
| **IEEE Transactions on Games** | 滚动 | transactions.games | 中高（适合 P2 扩展版，篇幅 + 完整消融） |
| 中文期刊（软件学报 / 计算机学报 / 模式识别） | 滚动 | — | 中（兜底；现有文档体系是中文，整理成本低） |

---

## 7. 统一优先级（把两份评估合并成一条可执行路径）

**P0（本周，不做则后面全部白干）**
1. `git init` 两个仓库 + 修 `.gitignore`（权重走 LFS/release + SHA 清单）+ 根 `README.md` + `requirements.txt` + `LICENSE` + `CITATION.cff`。
2. 许可声明与"起点为公开权重"表述写进 README 与论文模板。
3. 给 vcmi-gym 上游作者发邮件：引用 issue #5、说明起点与许可遵从、问是否愿意合作/共同引用。

**P1（2 周，零算力，产出可引用的短文）**
4. 13 候选 dev→test 选择偏差重采样（**配对场景 bootstrap**）+ ICC + 候选排名相关性。
5. 冻结诊断（`research/frozen-final-diagnostics.json`）的角色分层效应量与聚类区间。
6. 口径对照：按"是否计截断""是否按场景聚类"重算 3072 局，展示同一批数据在不同口径下的差别。
7. 写成 6 页短文 → arXiv 预印本 → 投 workshop。

**P2（4–6 周，跑游戏，产出主线论文）**
8. **新冻结确认集**（32 个新场景，使用前写死协议；旧 512 局已污染，不可再作独立证据）。
9. **基线矩阵**（random / heuristic / BC-MLP / BC-GNN / search-4 / 公开 MMAI / 选定模型）同套件同种子同协议。
10. **正对照 ×2**：弱先验（BC-MLP）跑同 PPO 流程；以及"从零训练小模型"链路的复用与扩充。
11. **3 个训练种子**（主实验 + 两个对照）。成本很低：单组 PPO 98,304 采样、wall 286–302 s、24 并发；瓶颈是工程编排与锁管理，不是算力。
12. 英文图表：胜率+聚类区间、训练曲线、argmax/KL 学习幅度、按兵种家族分解、角色分层——目前**只有 2 张中文图、0 条曲线**，这是最容易被外行审稿人一眼看出的短板。

**P3（顺延）**
13. 基准套件打包（文档、镜像、leaderboard 承诺）→ NeurIPS D&B 或 CoG。
14. 战略层单独立文：仅当招募主线跑出独立提升；否则作为 P2 的"局限与未来工作"一节。

---

## 8. 三条红线（与原评估一致，作为收尾）

1. **不追 95%**。把目标从"打败基线"改成"解释为什么没打败、以及评测为什么会骗人"。后者你已经做到了，前者没有。
2. **不合并候选**。13 个候选里挑最好的几个拼成绩 = 论文自杀。
3. **不隐藏失败**。失败记录带 SHA、带审计，是资产；写成"尝试 X、失败 Y、证据 Z"比写"SOTA"更有说服力。

**补充第四条（本次核查新增）**：
4. **不写"首创"**。2015 年已有 VCMI 大尺度策略 RL 的学术论文，2026-09 已有战略层 fork 的公开宣布，且你的战斗主线起点是上游公开权重。首创性只能落在"**可审计、可复现、保留阴性结果**"上——这已经足够成篇，且是真的。

---

## 9. 需要你拍板的三个决策

1. **先走"零算力短文"还是"直接补实验"？**
   推荐**先走零算力**（原评估 P1：13 候选选择偏差重采样 + ICC + 口径对照）：1–2 天出数字、风险极低、顺带把 P2 的统计框架搭好；而且它**顺带暴露**你在正式实验前就该知道的东西——如果 48 局 dev 的选择噪声确实有 ±9 个点的量级，那么"只跑 1 个种子 + 16 局 DEV"的现行评测方式在方法论上就先站不住。

2. **代码是否开源、什么时候？**
   无论投哪个会，代码都得能被人看到才有"审计级"的说服力；但**公开时机**取决于战略层主线是否还在跑。建议：**协议与评测代码现在开**（Apache-2.0，附许可与来源声明），**战略层与尚未跑完的实验暂缓**，避免半成品被当成最终成果反复引用。

3. **要不要联系上游作者（smanolloff）？**
   建议**要**，而且成本极低：一封邮件同时解决三件事——引用与许可合规、新颖性表述的合法性、以及一个潜在的合作者（他手里有完整的训练 fork 与发布流程，你手里有审计链与战略层原生集成）。**在投稿前把这封信发出去**，比在 rebuttal 阶段解释"我们的起点是您的权重"要安全得多。

---

*本复核基于 2026-10-23 21:45 的仓库快照与当日公开检索结果。仓库中另有并发会话产出的 `PAPER_FEASIBILITY_20261023.md`，两者结论一致，本文件为增量。*
