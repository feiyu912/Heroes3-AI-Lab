# 统一示范导入与BC门禁

此工具只读JSON/JSONL/gzip及证据文件，不启动VCMI、GPU或媒体下载。当前没有真人结构化轨迹；人工JSONL样例明确为拒绝测试fixture，不代表真实玩家操作。原Human v1运行脚本未修改，当前PPO与专家pilot保持原协议。

## 三种来源与身份边界

统一格式见 `expert_demonstration_schema.json`。`source.kind`为`script`、`search`、`human_structured`：

- script：脚本/规则专家；只有证据门禁通过才称“已验证脚本”。名称含Expert并不自动获得认证。
- search：传统BattleAI或搜索教师，记录实际算法/深度/版本；不能默认最优。
- human_structured：真实玩家通过存档、回放或原生决策边界记录的操作。必须是`trajectory_origin=human_recorded`与`action_origin=human_recorded`。

工程实验重建用script/search配合`trajectory_origin=experimental_reconstruction`，来源可以指向高手讲解，但动作仍是本实验执行，不能记作高手原始操作。`engine_execution`表示本地教师/脚本实际执行。视频猜测动作`video_guess`、视频来源类型与非法动作会被拒绝为结构化轨迹；讲解推断请存知识库，不进入动作记录。

`creator/version/source_reference/permission`未知写null；观察、合法动作、数量或终局未知同样写null，不能以0代替未知战损。缺失字段与明确null不同：必需字段必须存在，null可保留待完善记录，但不会获得Q3训练许可。不能从不准确视频坐标补造动作ID。

## 文件结构

JSON/gzip bundle包含四个顶层字段：`schema="expert-demonstration-v1"`、`source`、`episode`、`decisions`。episode必须包括battle_id、tactic_id、scenario_seed、actor_side、rules_version、outcome、permanent_army_loss、quality_tier和verification_evidence。

每个decision包含：

| 字段 | 含义 |
|---|---|
| observation | 当前玩家可见图nodes/edges及active_action_ids |
| legal_actions | 与该观测active_action_ids顺序一致、非空、无重复的整数ID |
| expert_action | 当前合法动作中的实际动作；未知为null |
| actor_side | 0 attacker或1 defender，与episode一致 |
| tactic_id/battle_id/scenario_seed | 追溯对应任务、局和种子 |
| expert_version | 人类采集器/脚本/搜索教师的实际版本 |
| action_origin | engine_executed / human_recorded / unknown |
| action_value | 可选数值未知写null，评价方法另存证据 |

outcome格式为`{"terminated":true,"truncated":false,"terminal_outcome":{...}}`。terminal_outcome沿用原生result_type、winner、initial_armies与casualties，不能只有“赢了”文字；永久军力损失按各兵种数量记录。当前普通无复活/召唤局采用结算伤亡与原始军队校验；复活/召唤等规则需要扩展结算审计，不能直接套用。

JSONL首行是`{"record_type":"episode","schema":"expert-demonstration-v1","source":{...},"episode":{...}}`，随后每行是`{"record_type":"decision",...上述decision字段...}`。同一文件仅一局，双方角色分别记录，不混合两方观察。JSONL允许gzip压缩。

## 门禁与运行

在已配置WSL内运行，不需要run-lab或游戏：

```bash
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/expert-knowledge-v1/validate_demonstration.py HUMAN.jsonl --mode audit --output audit.json
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/expert-knowledge-v1/validate_demonstration.py HUMAN.jsonl --mode bc-q3 --output gate.json --normalized-output normalized.json
```

工具检查schema所用的类型/枚举/必填/数组/常量/长度/模式约束、动作与mask一致性、逐步身份、原生胜负/存活兵力/伤亡。退出码0为指定门禁通过，2为拒绝；`--normalized-output`仅导出结构合法数据，并拒绝覆盖旧文件。结构合法的记录可规范化保存，但导出并不意味着BC获准，消费方仍须检查对应`bc_*_eligible`结果。

| 模式 | 通过条件与用途 |
|---|---|
| audit | 格式、身份与已提供动作合法；可显式保留未知，不能据此声称训练就绪 |
| bc-exploratory | Q2及以上、无关键未知、合法动作完整、正常结算；仅探索性拟合，不能称真实专家认证 |
| bc-q3 | 上述条件，Q3/Q4、source.verified=true，来源及战术质量证据均通过；缺正常终局直接拒绝 |

合成validator fixture永不允许进入训练。Q2标签只表示合法候选，不表示每步最优或真实高手示范。当前v1.gz可兼容读取；工具复用`audit_human_pilot.py`核验原canonical报告、gzipSHA、冻结脚本/地图/模型以及原生记录，并规范化为script/search来源、`verified=false`、Q2。模型baseline轨迹不冒充专家数据。

## Q3证据契约

source.verification_evidence与episode.verification_evidence均为`{"path":"...","sha256":"..."}`。引用本地JSON证据必须具有`schema="expert-evidence-v1"`、正确scope、相同battle_id、`passed=true`及checks字段：

- scope=source：source_traceable、permission_confirmed、not_video_inference全部true。
- scope=tactic：rules_compatible、replay_legal、normal_outcome、action_quality_compared、counterplay_tested、random_variants_tested全部true。

证据应由实际来源审查、原生回放/规则与配对实验生成，附原始局、规则版本和比较方法；不得手填true伪造通过。这个门禁验证记录完整性、证据文件SHA和审计声明，不自行模拟游戏、证明教师最优或认证真人身份。独立审核仍须阅读证据与原始记录；一个伪造但自洽的JSON不是可靠实验证明。

## 已执行验证

运行：

```bash
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/expert-knowledge-v1/test_demonstration_gate.py
```

实际结果见`demonstration-gate-check.json`：

1. 真实v1龙场景15决策gzip通过Q2探索门禁，明确不是Q3。
2. 同一真实数据被bc-q3拒绝：来源未认证、质量Q2、缺来源与战术证据。
3. 人工非法动作JSONL被拒绝，明确检测到expert_action不在合法列表。
4. video_guess动作被拒绝，不能冒充真实人类结构化操作。
5. 未知终局/战损被Q3拒绝。

`synthetic-*-example`文件均是测试样例，并非真实人类数据。当前未构建采集UI或录像理解，也未完成原生真人操作接入；下一步应从获准的人类存档/回放或交互采集器输出该JSONL，再通过回放及质量实验审核。
