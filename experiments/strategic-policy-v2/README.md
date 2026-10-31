# 可见威胁与补给战略接口 v2

本目录独立于冻结 v1。新增信息让目标选择模型能表达可见强敌和自城驻军；迁移初始权重的新输入列为0，尚未学会使用新信息，也未证明对 Nullkiller2 的独立提升。经济、招募仍由脚本执行，战斗仍委托原生 BattleAI。

## 严格观测协议

`strategy-candidates-v3` 保留旧全部字段，另必须显式提供：

```json
{
  "visible_threats": [{"position": [13, 10, 0], "approx_army_value": 3000}],
  "own_towns": [{"position": [8, 10, 0], "army_value": 5000}]
}
```

缺字段、null、旧 schema、NaN/负兵力会拒绝；只有显式空数组表示没有此类可见信息。`visible_threats` 的来源必须由原生层认证为当前可见敌英雄且仅用允许的 `getHeroInfo` 粗略兵力；Python只能验证数值结构，不能单凭收到数组证明其合法可见来源。自城坐标应与候选目标使用相同 visitable 坐标约定。

encoder version 为 `strategy-visible-threat-supply-encoder-v2`，state26维、candidate23维。原 state11/candidate15 的顺序和数值变换精确保留。附加 state15维包括可见敌英雄数/强敌数、最近强敌相对坐标及距离、最大敌我兵力比、自城数/总与最大驻军比、最近自城相对坐标及距离、可见敌军相对自城驻军的距离衰减压力。附加 candidate8维包括目标格自城驻军比、目标与next附近的强敌距离/敌军压力、目标与next到自城距离、目标附近自城补给压力。

完整稳定字段名在 `encoder.py` 的 `STATE_ADDED_FEATURES` 和 `CANDIDATE_ADDED_FEATURES`。兵力比用 `log1p(min(value/max(reference,1),1e6))/log1p(100)`；压力按 `1/(1+distance/6)` 衰减。距离为 `sqrt(dx²+dy²+(36×dz)²)`，距离特征再除36。上述距离和压力只是可见坐标近似，不是引擎路径、可达性、行动范围、实际拦截概率或战斗胜率。不得据此宣称模型预测了真实拦截。

## 显式迁移

新模型 format：`strategic-visible-threat-supply-prior-v3`。迁移 first-layer 的旧 `[state11,candidate15]` 列至新 `[state26,candidate23]` 时：

- old `[:,0:11]` → new `[:,0:11]`；
- old `[:,11:26]` → new `[:,26:41]`；
- new `[:,11:26]` 和 `[:,41:49]` 全0；其余层、bias 和固定 heuristic prior 完整复制。

因此新增信息无论为0还是非0，初始迁移模型与旧模型应给出相同的目标偏好和 value（不同矩阵形状/设备允许浮点容差）。非零梯度检查仅证明新增列可学，不证明已经学会。value 仍未校准，不能当作胜率。

已生成 `checkpoints/threat-supply-initial-v3.pt`，SHA `804aab1aeb3fcc7e685891b469abe1efaf309399619f4d47771382f3d70571d0`，父模型为 v1 新原生机制连续训练的 `takeover-03/native-boundary-01/continuous-2/update-2.pt`，SHA `f524796161915cb43ae9e228f13dd72c195df016ce5d2c25dab7d8a7d2aeb7cc`。checkpoint 保留完整旧 lineage 与父协议/132历史step；新增协议 optimizer=None、step=0、training_updates=0，明确不是 optimizer resume。更早 pilot02 的两次更新仍在 lineage 中，不抹掉也不混入新协议步数。

重新迁移须新文件，禁止覆盖父权重或已有输出：

```text
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/migrate_checkpoint.py --source /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/takeover-03/native-boundary-01/continuous-2/update-2.pt --out /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/checkpoints/new-migration.pt
```

## broker 与真实 smoke

`broker.py` 与 `smoke_game.py` 支持四种明确模式：

| mode | 模型输入/行为 |
|---|---|
| heuristic | 严格v3校验，按既有 heuristic_score argmax，无神经模型 |
| legacy-policy | 严格v3校验后显式投影旧11/15编码，忽略新增特征；使用指定旧checkpoint，在新原生条件下作为baseline |
| new-policy | 新26/23编码、新format模型；无隐藏脚本override；`policy` 是此模式别名 |
| supply-aware | 先按legacy-policy求baseline，再调用独立 `supply_policy.choose(request,baseline_index)`；属于显式脚本补给干预，不是学得收益 |

ready与逐动作审计记录 mode、model_scope、模型SHA及代码SHA。只有 supply-aware 调用补给脚本，逐动作另记录 baseline_index/override_reason，并冻结 supply_policy.py SHA。其他模式不含此隐式规则。

运行 `smoke_game.py` 会真正启动游戏，资源锁由主 runner 管理；本次 CPU 验证没有执行它。示例为新策略：

```text
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/smoke_game.py --mode new-policy --checkpoint /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/checkpoints/threat-supply-initial-v3.pt --map Maps/adv/takeover-v2-train-01-mines --red DirectorAI --blue Nullkiller2 --seed 2026101912 --tag threat-supply-new-smoke
```

legacy-policy/supply-aware 模式必须使用上文父 v1 checkpoint，不能传新格式冒充旧模型。运行过程中不得修改被冻结源码、模型和原生输入。

## CPU 证据与训练入口

`selfcheck_cpu.py --out <新唯一目录>` 可复现迁移输入列重排、旧前缀/mask精确保留、logit/value数值一致、附加信息改变编码但不改变初始迁移行为、额外列有限非零梯度、checkpoint保存加载、缺字段/旧schema/NaN拒绝，以及实际文件 broker 的两个合法请求和一个非法请求不回动作。随后执行实际 trainer CPU preflight，强制任何CUDA RNG调用报错。没有原生游戏、optimizer step或CUDA context。

首轮证据 `cpu-selfcheck-01/AUDIT.json`：迁移logit/value最大误差均0；四种broker模式均通过。该检查只用合成可见字段，不能代替native合法可见信息认证，也不构成课程收益。

`train_ppo_pilot.py` 复制适配 v1 已加固保存/真实step/边界恢复实现，新请求/encoder/model格式和协议均独立。默认加载上文v2迁移权重；`--initialize-from`只接受新format权重，旧文件须先用迁移工具；`--resume`仅同新协议完整update边界。`--preflight-request`可指定真实v3请求，默认 `fixtures/visible-request.json` 明示为合成样本。

```text
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/train_ppo_pilot.py --out /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/new-cpu-preflight --preflight
```

训练入口目前只完成CPU预检，尚未启动v2 GPU训练；算法仍继承原终局奖励PPO配方。应先验证native额外信息和真实失败机制，再决定新冻结实验，不能靠增加同配方次数假装已解决NK弱点。
