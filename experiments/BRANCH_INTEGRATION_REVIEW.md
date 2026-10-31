# Human Expert Learning 支线只读接入审查

2026-10-16。对象为`G:/Heroes3-AI-Lab-worktrees/human-expert-learning-v1`，实际HEAD `5e3a7152d3ea8d3cc4626f4802480c3e50ac1fbf`。主要审查`tools/human_expert/ppo_adapter.py`、`curriculum.py`、`opponents.py`，对照当前root的OpponentVector、vector_env、Reference PPO和实测产物。没有合并代码/模型，没有运行游戏或训练，没有修改活动代码。

**建议复用工程接口和记录契约，保留支线失败证据；不要直接把其smoke当作混合专家PPO训练器，也不要采用其BC权重替换当前基线。**

## 已运行到哪一步

核对RESULTS.md与evidence中的comparison、retention-comparison、script-bc.training、policy-freeze、ppo-smoke-v11记录：

| 项目 | 真实记录 | 可支持的范围 |
|---|---|---|
| 脚本数据 | 4局全败，63条结构化转移，每局有一次合法无友军目标的多敌攻击 | 可执行脚本示范；不证明逐步最优或战术净收益 |
| BC | CPU40步，只改policy head；NLL 23.5181→16.1328 | 拟合provisional script labels，真人动作0 |
| 独立小对照 | baseline4/8→BC4/8；阵亡单位87.875→93.125 | 没有胜率提升，平均阵亡增加5.25；不能发布为学会高手战术 |
| 普通小回归 | 2/4→2/4；阵亡64.5→63.0 | 小样本未见净胜变化，不能认证没有遗忘 |
| PPO接入smoke | 64步、56次脚本请求、3个正常终局、4次安全多目标选择、1次更新；logp重算误差3.8147e-6 | 真实双端请求和PPO数学接口曾跑通；不是完成混合课程/反制训练 |
| 混合课程 | 生成train-only配置清单，记录executed=false | 调度输入存在，不能称已训练50/30/20 |

8条件结果有一局负转胜、一局胜转负，净变化0。多目标攻击10→13并没有转化成更好结果；一例防守对历史MMAI从胜转负，另有训练后图目标含友军的攻击。阵亡指标是单位数量而非价值加权损失；动作覆盖也不是实际伤害。

branch reports另记录完整逐步游戏回放与21局/401转移审计。本次没有重跑这些游戏；本次root只复验`test_protocol_layout.py`，1项形状/类型与终局防篡改单测通过（约0.004秒）。离线单测通过不等于本次重新执行了逐步引擎回放。精确观测训练/测试交集0只排除完全相同状态，不证明跨来源/布局独立泛化。

## 可以复用的接口

1. `ExpertOpponent.__call__(observations)->list[int]`符合现有OpponentVector的中央对手回调，返回当前合法动作ID，剔除teacher/terminal审计旁路信息。原生BattleAI和CPU ONNX历史对手可以继续在各worker运行，脚本专家仅用于指定OTHER_ENV通道。
2. `curriculum.build`返回category/scenario_id/source_split/config/peer_adapter，保留train-only筛选、可复现seed和对方角色正确的ONNX模板，适合派生新的明确版本调度器。
3. `protocol.Recorder`的shape/dtype元数据、前后状态和哈希链有价值，可结合root实际schema codec。它明确state_after可能包含对手动作，native_events=null；不把状态差冒充即时伤害事件。
4. 脚本不读教师动作、真实失败保留、模型冻结后比较、独立失败不回写为成功，这些工程边界应保持。

## 接入前必须处理的陷阱

### 1. 不是当前Reference PPO训练器的可直接替换对象

当前conservative trainer从`fixed_opponent.pair`取得冻结公开策略作为reference。支线ExpertOpponent没有pair，`assert_unchanged()`仅恒返回True（opponents.py:56），不能用它直接替换公开神经对手对象后继续原引用逻辑。

应将“训练对手”与“冻结公开reference”拆为两个明确职责：脚本服务OTHER_ENV，公开pair仍独立冻结并用学习器原始obs独立编码计算KL。公开参考不能变成脚本argmax，也不能给不同body借用学习器编码。参考参数须与learner/optimizer分离。若同一训练池既要中央公开MMAI又要中央专家，需按连接/worker元数据路由；目前OpponentVector把所有中央请求交给一个callable，不能靠兵种猜来源，也不能把private路由标签灌入策略观测。

### 2. smoke只取一个训练地图、一个角色

ppo_adapter.py:33–39筛训练集后只取cases[0]、固定attacker、固定seed781377、单worker；没有读取curriculum输出。随后只执行一次rollout和一次PPO更新。64步实测不能证明多地图、攻守互换、普通/专家/历史池或跨反制能力。

真正混合trainer应消费冻结的全部configs，逐worker记录category、scenario family、角色、对手版本，采用共享池锁与恢复协议。环境步数应按rollout×worker数记录，不能扩成24worker后仍保存args.rollout。

### 3. 24环境时比例和角色偏差

curriculum.py:16–22重复固定十项序列ordinary×5、expert×3、history×2，并以全局i奇偶分角色。20配置时确实10/6/4，但当前24配置会是14普通/6专家/4历史，即58.33%/25%/16.67%，不是50/30/20。

每个十项块ordinary为3进攻2防守，expert为1进攻2防守，history各1；重复偶数长度块不会消除类别内角色偏差。现有test_curriculum只检查20配置总数和全体角色集合，未覆盖24配置及每类别角色平衡。

下一版应明确整数配额/周期累计比例，分别对category×role分层分配；例如24环境可在多update周期轮换配额与角色，而非把取整当精确比例。报告实际决策/样本占比，不以配置比例代替有效经验比例。地图通过有放回随机采样选取，仍需审计family覆盖，不能假定每张训练图都出现。

### 4. 场景参数没有完整传到worker

curriculum config仅带map/role/seed/opponent/feature_version等；当前vector_env调用lab.make_env固定规则，没有传tight_formation_chance等专项参数。支线报告已注明loose setting不同于tight夹具，不能把tight专家验证结果当训练环境同一分布。

接入前应核查每个生成场景要求的阵型、英雄、障碍、步数、loss_shaping、step_cost等是否实际生效。只能通过当前worker支持字段时，先明确收窄为真实可执行分布；需要新增参数则在隔离版本实现并逐项验证，不热改正在运行的原worker。

### 5. “安全多目标优先”是强偏置，不是收益专家

opponents.py:15–16和36将所有无友军目标、至少两敌目标的范围攻击作为强制候选子集；存在这种动作时，即使单目标击杀更重要也不能选择它。score又用relative VALUE_REL覆盖代理，缺预计伤害、击杀、反击、位置暴露及后续时序。正是支线“多目标变多、胜率不变/战损上升”的一种待检验机制，不能称已证明因果。

facts.ability来自复用root coverage.assess，包含龙喷吐及尸巫死亡云；VERSION名称visible-breath不表示只处理龙。未来课程标签应明确区分能力和规则，不把所有范围攻击都叫喷吐。普通greedy变体同样使用覆盖/威胁代理，只去除强优先；它也不是可靠强基线。无安全范围机会时仍可能选择含友军目标的动作，不能把safe_multi计数等同全局无友伤保证。

可把该策略当有已知偏差的对手/反例生成器，配对测试“利用其强制范围优先”与更合理响应，不能无条件蒸馏整个轨迹或拿它替换BattleAI。反制是否有效需要合法对照、原生伤害/永久损失和未见变体；脚本名字不赋予质量。

### 6. 参数冻结、重算与恢复要采用当前严格契约

ppo_adapter.py:32把全部requires_grad参数交Adam，但rollout用encode_features的inference缓存，实际图body梯度不会回传；这相当于缓存头部更新路径，不能称full-graph PPO。建议显式冻结body，明确policy/value哪些更新，逐参数核对并保存准确trainer模式，避免未来换编码器后默默扩大更新范围。

smoke调用原update默认重算批量4，而采样批量为1；默认atol/rtol均2e-5，与当前24采样/明确2e-4绝对、0相对重算协议不同。CPU这次误差很小，不证明扩到24 CUDA仍一致。新路线直接复用当前reference_ppo严格门禁：按原推理批量重算、同候选顺序、有限梯度、公开reference冻结。保留GAE对truncation的bootstrap逻辑，但另报截断和原生异常，不只数terminated。

smoke保存optimizer和CPU torch RNG，只能支持其限定实验恢复；缺完整训练config、numpy/CUDA RNG、对手/数据冻结、定期checkpoint、真实退出与恢复续训证明。不得把这份checkpoint混入支线40步BC的独立对照，也不能加入root已冻结的最终候选。

### 7. 依赖与对手池仍需完整冻结

opponents.py经bootstrap.LEGACY加载root human-tactics-v1/experts.py；protocol也加载旧run_episode.py。支线本地code_sha和episode冻结涵盖自身与research文件，但所读冻结逻辑没有显式加入这两个LEGACY实现文件。它们在本轮没有已知变更；这不推翻已发生的运行，但未来只固定worktree commit不足以固定整个策略实现。派生版本应一起固定所有实际导入依赖SHA/引擎/ONNX/地图，增加配置不可变检查，不能沿用恒True的assert_unchanged。

所谓history当前是单一history_model_template，默认仍指公开原MMAI，不是已经实现多个历史checkpoint池。模型模板的攻防映射正确，但多版本池更新、样本配额、历史性能和策略漂移仍需实现。

## 数据质量与root路线重合

支线63标签来自4局失败的脚本轨迹，明确provisional；root185标签来自6个正常获胜专家局，明确Q2探索；两者都不证明每步动作最优，不能混称Q3或获授权真人操作。失败轨迹可以用于对手/反例和价值学习，但不应在无逐动作质量证明时整局当正向高质量BC。root四条来源WAIT首步还有幽灵龙老化/随机伤害混杂，和支线喷吐代理不是同一种证据；保留来源/label_gate/family和失败边界。

两路均复用B64同SHA、RecoveredPair/图编码缓存/Policy头、合法mask、普通BattleAI与MMAI基准。不要重复注册来源、把同一图状态算两条独立人类经验，或累加两路胜场制造新总体胜率。支线的两个测试家族已读，仅作为该支线固定小样本证据与失败诊断；新混合路线需开发数据选模型后另冻未读确认集。

## 推荐最小派生方案

先保留当前活动实验。新隔离版本只借鉴三个部件：公开观测脚本回调、显式category/role配额清单、shape/dtype/状态链数据适配；不合并模型。用固定公开pair作独立reference，普通BTAI/原生MMAI/已知偏差专家三路分别标记，明确配置生效范围和严格重算。先证明多类别多角色rollout/恢复/参考不变，再进行等预算BC、专项PPO、BC+PPO、加历史池对照及普通保留检查。源数据只在既定质量层使用，原生事件缺失时战术成功率保持不可评估。

此处只给接入建议，未创建新adapter、未进行混合训练或重跑任何游戏。

## 当前活动控制器的额外只读记录

root确认expert-retention-v1 validate_model读取control.get('state','')，sourceBC writer实际使用status（queued/training/evaluating/completed/failed）。活动控制器源码已冻结，不热改。本次正常成功报告/freeze路径不受影响，但source上游失败可能无法被识别，root已承接实时监控并在失败时安全处理等待。下一个非活动版本应兼容state/status并对冲突拒绝，不用原始failed控制覆盖恢复状态；本审查未改活动文件。
