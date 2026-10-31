# Native planner horizon pilot：4未优于2

已真实执行16局（2个已使用训练场景×双方角色×2种子×horizon2/4），全部原生正常终局、0非法/截断，最后事件保存完整。未看development/test，未扩到10，未BC，未更新/替换B64。

8个配对单元中，horizon4相对2主力平均**多损0.5**，净胜**-2**。两次回退都在训练场景1守方。未获更强教师，不能因模拟更久就声称更聪明。

实际原生 CPU teacher_eval_us：horizon2 总190234微秒/186决策，均值约1.02毫秒；horizon4 总203413微秒/184决策，均值约1.11毫秒。每个决策原生 description 和时间已归档；这与Python读取teacher action的耗时不同。全部为CPU规则模拟/评估，没有CUDA参数更新或强化学习训练。当前小场景的成本可接受，但目标近似误差比速度更需要解决。

## 代码审计

ML-on事件运行时 `AI/MMAI/BAI/v15/BAI_v15.cpp:398-409`：先从StartInfo取得默认simulationTurnsCount，再用 LAB_BATTLEAI_TEACHER_TURNS覆盖；只接受2/4/10，传3会抛 `Teacher horizon must be 2, 4 or 10`。参数进入 BattleEvaluator 构造，不是未消费的环境变量。此pilot不改native文件，也没有声称运行3步。

`AI/BattleAI/BattleAI.cpp:112`：普通BattleAI默认由难度选择2或10，并非由LAB_BATTLEAI_TEACHER_TURNS控制。teacher使用同类评估器不等于与对手配置相同。

`AI/BattleAI/BattleExchangeVariant.cpp:710-729`：simulationTurnsCount控制交换turn循环，每轮遍历单位行动队列；超出已取队列时复用最后队列。它是有限范围的交换估计，不是每层穷举所有合法走位/双方所有应手的minimax树，更不是完整引擎反事实重执行。增加horizon不能补齐所有站位、攻击顺序、让先手与特殊能力建模问题。

`BAI_v15.cpp:412-440`：teacher结果通过side、stackNumber、actionType、spell及目标匹配到现有合法Action ID；runner仍强制合法性，并用真实事件核对执行。原生源码SHA与动态库/地图/新runner共同冻结，未原地重建。

## 产物与复现

PLAN.md为预注册说明；run_episode.py支持显式 --teacher-turns 2/4/10并保存实际原生时间；run_train.sh仅跑训练图0/1，已有完整证据核验后跳过、不覆盖；PAIRED_RESULTS.json包含逐配对损失/胜负与搜索时间；runs/train保留完整轨迹和SHA。重新执行必须使用新的输出路径。

后续如需更强教师，应验证更准确的反事实状态复制与合法候选评估接口，或检查交换评价的目标偏差，不能继续把10当必然升级。没有有效教师就保留原模型。
