# WAIT来源复现数据接口

来源为 `../source_wait_case.json` 所定位的 Hallas 原创文字攻略。所有兵种数量、位置、随机种子和脚本回应均为实验室重建，不是恢复的高手操作录像。

`source-wait-scenarios.json` 是当前运行的8张训练地图。`all-source-wait-scenarios.json` 是预先冻结的完整16张地图：8 train、4 development、4 test。独立测试只能在模型及专家规则冻结后运行。参数与来源冻结分别见 `wrapper-provenance.json`、`holdout-freeze.json` 和 `all-scenario-freeze.json`。

每个 `wait-runs/<case>-<policy>.json` 保存真实终局、逐步合法动作集合、选择动作、我方回合、对手操作数量、状态图与源文件哈希。运行复用原 `reconstruct_wait.py` 的单环境CPU脚本接口及全局评测池锁；内部历史配置名 `MMAI_GPU` 只承担另一方传输，不代表这里用了神经网络GPU对手。

`wait-train-comparison.json.results[]` 的稳定字段为 `case / split / normal_pair / wait_success / control_success / window_verified / wait_loss / control_loss / benefit_verified`。完成数应与8张训练地图核对，不能仅凭该文件存在宣称全部完成。

`candidate-bc-train.jsonl` 仅保存通过真实合法WAIT、跨轮窗口及正常终局收益门槛的**第一步**，没有把整条greedy轨迹都标为专家。每条记录包含：

- `observation.nodes`：原始节点特征数组。
- `observation.edges`：`[{relation:[源节点,关系,目标节点], index:二维索引, attrs:属性}]`。
- `observation.active_action_ids`：当前合法动作ID；动作ID只对该图有效。
- `action`：该状态下合法WAIT标签；`actor_side` 为0进攻方、1防守方。
- `round / step / tactic_id / battle_id / scenario_seed / expert_version`：样本关联及上下文。
- `paired_result / label_origin / label_gate`：配对对照的真实证据及标签由来。
- `aging_causal_confound_not_isolated=true`：幽灵龙老化和伤害随机性尚未做事件级因果隔离。

“合格”在此仅表示通过这个小实验的配对观测门槛，不代表证明普遍最优。没有收益的配对完整保留在比较表及raw报告，不进入正示范。所有样本都是同兵种家族、固定脚本对手下的局部实验，不能据此宣称战胜BattleAI或学会通用人类战术。

跨轮窗口正确也可能没有收益。一对一直接攻击后，慢兵回击会触发快兵自己的反击；这可以抵消等待创造的攻击次数优势。原文还明确讨论高速飞兵远离友军时被多队围攻的风险。因此另有预先冻结、尚需实际验证的 `../wait-variant-v3/` 多堆试点；其执行器只在v2既定8对全部无收益后自动启动，不读取dev/test调参。
