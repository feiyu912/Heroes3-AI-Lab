# 2026-10-31：训练瓶颈诊断与 BC 可行性结论

本轮是只读诊断 + BC 管线准备，没有启动新的原生对局、PPO 更新或模型晋升。
所有历史失败、冻结模型和 final test 保持原状。结论以仓库里的原始 `RESULT.json`、
`TRAIN_CREDIT_DIAGNOSTIC.json`、`DEV/RESULT.json` 和审计报告为依据，不以聊天摘要为依据。

## 0. 对 Codex thread 的访问确认

已实际读取本地 Codex 主线程
`01a166c6-eedd-7a91-a4a2-0c79d4aa785c` 的完整 rollout
（`~/.codex/sessions/2026/10/23/rollout-2026-10-23T11-21-15-01a166c6-...jsonl`，
4,280 条记录），并读取它的 10/25 续接 fork、10/26 子会话以及
`thread_history_1.sqlite` 中的 7 个 turn。线程最后一条用户输入是“*继续*”；
线程内没有一份新的 BC 数据集，只有已经落盘的 admitted samples、refill 机制证据和
prepared-but-not-run 的校准包。当前可读的训练数据入口见第 4 节。

## 1. 训练到底卡在哪里

### 1.1 战略 PPO 不是“学得慢”，而是当前协议没有可学的正信号

最近一次完整战略训练（`experiments/takeover-20261023/active-learning-delivery-01`）：

| 项目 | control | curriculum |
|---|---:|---:|
| 完整 TRAIN 局 | 8 | 8 |
| 其中 EmptyAI 胜 | 4/4 | 4/4 |
| 其中 Nullkiller2 胜 | 0/4 | 0/4 |
| 样本行 | 4,138 | 4,655 |
| 实际 Adam | 260 | 292 |
| PPO 更新次数 | 1 | 1 |
| 模型参数量 | 18,933 | 18,933 |

模型在训练前就已经 4/4 胜 EmptyAI；唯一有难度的对手 Nullkiller2 是 0/4。
所以 PPO 从 EmptyAI 得到的“正样本”是已经会的开局，从 Nullkiller2 得到的全是失败。
`TRAIN_CREDIT_DIAGNOSTIC.json` 的加权优势给出了直接证据：

| 组 | 行数 | 加权优势 |
|---|---:|---:|
| EmptyAI / move | 1,967 | +683.3 |
| EmptyAI / recruit | 958 | +136.2 |
| EmptyAI / build | 108 | +40.0 |
| Nullkiller2 / move | 556 | **-602.7** |
| Nullkiller2 / recruit | 99 | **-224.2** |
| Nullkiller2 / build | 22 | **-47.5** |
| Nullkiller2 / end_turn | 85 | **-36.1** |

同一批训练里，EmptyAI 的动作被正向强化、Nullkiller2 的动作被负向抑制，但
**request 里没有对手身份字段**。模型无法条件化“这是 EmptyAI 还是 Nullkiller2”，
只能在相似状态上收到互相冲突的梯度。这不是一个可以用更多 epoch 修好的超参数。

同时，8 局比赛只做 1 次 PPO 更新（4 epoch、260/292 Adam），KL 约 0.0033，
entropy 约 1.59，recruit bias 仅从 0 变到 +0.0147。模型的决策排序几乎没动。
这不是“PPO 收敛”，而是一次非常小的、带高方差Episode级奖励的更新。

### 1.2 终局 ±1 + gamma=1 的信用分配太弱

当前 PPO 使用完整对局的 terminal +1/-1，所有决策共享同一个 episode return，
`gamma=1.0`，没有 reward shaping，没有 GAE，没有 step-level credit。对一局
63–1,066 个决策的游戏，这等于“把整局归因为同一个标签”。它能做的只是：
赢了就提高这局所有动作的概率，输了就压低这局所有动作的概率。这更像
“按胜负筛选的行为克隆”，不是策略梯度信用分配。

### 1.3 种子、对手、地图被混在一起

8 个 TRAIN 格子的 seed 是 `2026104400+i`，每个 map/opponent/player 组合各自一个
seed；对局双方也没有配对到同一 seed。于是“对手难度”和“随机初始状态/资源”混在一起，
小样本下无法归因。评估只有 8 局（4 EmptyAI + 4 Nullkiller2），一次胜负翻转就是
12.5 个百分点，不能支撑“稳定提升”的结论。最近的 5/8→4/8 和后续 0/8→0/8
正是这种噪声的表现。

### 1.4 战斗线也已经到“方法/接口”瓶颈，不是单纯步数不够

战斗线累计 68 次更新、8,704 次 Adam、240 局/30 更新的批次后：

- 对 BattleAI 15/16；
- 对公开作者 MMAI 13–14/16；
- 终局信用、MC、学习率对照都没有净胜局收益；
- 96 局评估的置信区间仍然很宽，15/16 也不能证明 95%。

战斗模型的特征接口仍缺少逐堆原始 HP/数量/攻防速、完整英雄施法/攻城/撤退等；
继续在同一个接口上加 PPO 步数，边际收益很低。BC 不会自动补上缺失的观测和动作。

### 1.5 完整目标还缺“决策面”

当前战略策略是**单英雄**的 `move/end_turn/build/recruit`；战斗委托原生 BattleAI，
免费转兵是脚本。多英雄调度、城镇神经经济、雇英雄、兵链、飞跳/回城、主动魔法
都不在这个动作空间里。英雄无敌 3 高手的视频往往讲的正是这些内容。
所以“把视频里的方法做成 BC”必须先回答：这些方法能不能映射到当前候选列表？
不能映射的部分，BC 训练不出来，只能先扩接口。

## 2. “最强 AI”现在到底在哪

- 局部战斗：最强候选是历史 v6 组合模型和 battle-terminal-credit 的 control68 一带，
  对 BattleAI 约 15/16，对公开 MMAI 约 13–14/16；目标是 95% 仍未达到。
- 完整战略：对 EmptyAI 4/4，对 Nullkiller2 0/4；没有稳定收益，也没有晋升模型。
- 完整对局：仍是单英雄 + 脚本经济 + 原生战斗，不是完整 1v7 战略 AI。
- 人类战术：只有机制级验证和少量探索性 BC；没有认证的高手轨迹，也没有
  经独立测试证明的整体收益。

因此，当前最重要的不是再跑一次 8 局 PPO，而是给战略策略一个**可学习的正先验**
和**足够大的训练规模**。BC 是合适的工具之一，但必须先满足下面的数据条件。

## 3. BC 适不适合这个项目：结论

### 3.1 机制上适合

当前模型是候选打分器：

```
state(35) + candidate(43 + 34 + 150 creature one-hot) -> hidden 64 -> logit
```

BC 只需要对每个 request 的 logits 做 masked cross-entropy，标签是
`candidates` 数组里的下标。这与 PPO 的候选分布完全同构，不需要改动作空间。
模型只有 18,933 个参数，BC 计算量很小，真正的瓶颈是数据质量而不是 GPU。

### 3.2 但“视频讲解”不能直接当标签

项目已经有明确的失败记录：

- `experiments/human-tactics-events-v2/TRAINING_RESULTS.md`：205 条探索性标签，
  policy-head BC 的 NLL 从 10.47 降到 7.64，但独立 8 局测试平均损失反而 +8.12，
  不建议晋升。
- `experiments/human-tactics-events-v3/CURRICULUM_RESULTS.md`：v1/v2/v3 三版
  WAIT/诱饵课程均未通过预注册门槛；机制命中不等于收益。
- `experiments/expert-knowledge-v1/synthetic-video-rejection.json`：`video_guess`
  动作被数据门禁明确拒绝。
- 早期 battle BC：teacher top-1 63.3%，独立胜率只有 26.9%；后来 PPO 才把
  同一初始化的胜率提高到约 55%。**BC 拟合 ≠ 战斗/对局强度。**

所以，如果其他电脑只产出“看了视频后推断的动作”，BC 训练会重演这些失败。
可接受的路径只有两条：

1. **规则教师 + 真实引擎执行**：把视频里的方法写成确定性 teacher，在真实
   隔离引擎里跑 TRAIN 地图，由引擎记录 request 和 teacher 选择的候选下标；
   这是 `experimental_reconstruction` / `engine_execution`，最多算 Q2 探索性。
2. **真实人类轨迹**：有实际 replay/save/决策边界记录，能证明是真人当时的选择；
   这才是 `human_recorded`，并且还要通过项目的证据门禁才可能到 Q3。

### 3.3 BC 应该放在 PPO 之前，而不是 PPO 之后

- **BC → PPO**：推荐。BC 提供一个比随机/零先验更好的起点；PPO 再从真实胜负
  微调。进入 PPO 时必须新建 Adam/RNG，不能把 BC 优化器当 PPO 优化器。
- **PPO → BC（纯 post-training）**：不推荐作为默认。纯 BC 会覆盖 PPO 学到的
  探索行为；如果教师并不比当前策略强，结果会退化。只有在教师明显更强、且
  保留 KL/辅助 BC loss、并用配对评估证明不退化时，才值得做“post-training”。
- **BC + PPO 混合**：可以在 PPO loss 中加入 `KL(pi_BC || pi)` 或 expert-batch
  的辅助 CE，防止遗忘。这是比“最后再做一遍 BC”更稳的做法。

### 3.4 数据量和覆盖要求

- 第一次 BC 至少 10,000 个唯一决策；要覆盖多地图/双角色/双对手时，建议 50,000+。
- 训练/验证/测试按**整局/地图/seed**划分，不能按单步随机划分。
- 至少两类对手（EmptyAI + Nullkiller2）都要有成功或高质量教师轨迹。只有
  EmptyAI 的胜利数据，学到的仍是“打空 AI”。
- 教师必须在同状态下比当前学生更好；否则 BC 只会让学生更自信地犯错。
- 当前动作空间只支持单英雄 move/end_turn/build/recruit。多英雄、雇英雄、城镇
  经营、兵链、魔法等视频内容，要么先扩接口，要么明确排除。

## 4. 已准备好的 BC 管线

目录：`experiments/strategic-bc-20261031/`

| 文件 | 作用 |
|---|---|
| `bc_common.py` | 加载 frozen encoder/model、固定 150 生物 catalog、BC checkpoint 格式 |
| `validate_dataset.py` | 严格校验 schema6 request、候选下标、split 泄漏、catalog、Q0/video_guess |
| `train_bc.py` | masked candidate CE + 可选 value loss + 动作类型加权 + episode 级 holdout |
| `README.md` | 运行方式、已知集成不兼容点 |
| `DATA_CONTRACT.md` | 其他电脑应交付的 JSONL 格式、来源分层、质量门和覆盖要求 |

已做的实际检查（不是能力结论）：

- 用真实 admitted `samples.jsonl`（799 决策）跑通 validator：
  `move 483 / recruit 218 / end_turn 87 / build 11`，0 错误。
- 用其中 200 条在 CPU 上跑 1 epoch 的 smoke：checkpoint 可保存、可重新加载、
  前向 logits/value 有限；训练集 top-1 0.575。这个数字只证明代码通路，
  不证明任何对局强度。
- `bc_common.load_any_checkpoint` 可从 `1510149e` 初始化或 `b52ac74a`
  控制模型加载；两者都是 18,933 参数。

### 当前不能直接接 PPO 的地方

- `model_io.initialization_model` 要求 prior-zero 初始化、`recruit_actor=0`、
  `recruit_bias=0` 和旧的 lineage；BC 权重一定不满足。
- `train_update_v3.py --resume` 要求完整 PPO Adam/protocol/RNG 边界；BC 的
  Adam 不能冒充 PPO 优化器。
- 运行时 broker 目前调用 `model_io.load_model`；需要一个新的 BC loader 或
  隔离的 BC broker。**不能把 BC checkpoint 改名成 PPO resume。**
- 这些是集成工作，不是数据问题；在 BC 数据到达前可以单独做，不应改冻结文件。

## 5. 其他电脑交付后，这边实际要跑的顺序

1. 收数据：`train.jsonl` / `validation.jsonl` / `test.jsonl`、`DATASET_AUDIT.json`、
   `TEACHER.md`、teacher 源码 SHA、catalog/encoder 版本。
2. 先跑 `validate_dataset.py --quality-gate q2 --require-split`；有 Q3 证据才用 q3。
3. 跑 `train_bc.py`，记录 base SHA、数据 SHA、每类动作 top-1/NLL、验证集曲线；
   不做 test 选模。
4. 用隔离 broker 加载 BC 模型，跑配对原生评估（至少 32 局/臂，双角色，EmptyAI+NK）。
5. 只有 BC 在配对评估中不差于基线，才进入 BC-initialized PPO；PPO 使用新
   Adam/RNG，并保留 KL/辅助 BC 约束。
6. 任何“更强”结论都必须来自冻结模型后的独立评估，不能来自 NLL/top-1。

## 6. 对“最强 AI”的下一步建议（按优先级）

1. **先补正先验**：用规则教师/NK 轨迹/人类轨迹生成 BC 数据，而不是继续
   8 局 PPO。当前 PPO 的负优势组全是 NK，缺的是成功经验。
2. **把对手身份/难度纳入条件**，或者至少把 EmptyAI 和 NK 的训练批次分开，
   避免同一状态被相反标签拉扯。
3. **配对 seed**：同一地图/角色/seed 下跑 EmptyAI 和 NK，或者至少把对手作为
   显式输入。否则无法判断是策略还是随机初始状态导致胜负。
4. **把评估从 8 局提高到 32–64 局/臂**，并报告 Wilson 区间；8 局只能做方向性
   smoke，不能做晋升。
5. **训练规模**：一次 PPO 更新不是训练。若继续 PPO，需要几十到几百次更新、
   足够多的 on-policy 对局；但在这之前先解决“没有 NK 正样本”和“对手不可观测”。
6. **接口扩展**：多英雄、城镇、雇英雄、兵链、魔法是视频内容的主体；不扩接口，
   BC 只能学到一个很窄的单英雄策略。

## 7. 结论一句话

**BC 在机制上完全适合这个项目，但现在最缺的不是 BC 代码，而是“可执行的教师标签”
和“能被当前 35+227 维候选接口表达的高手决策”。** 如果其他电脑交付的是
引擎执行过的规则教师轨迹或真实人类轨迹，我们可以立即验证并训练；如果交付的是
看视频推断的动作，应该先拒绝，改成 teacher + 引擎回放，否则会重复 205 条标签
BC 的失败。
