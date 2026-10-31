# Native planner pilot v1：模拟 horizon 2 与 4 配对

先只读核查，后实验。实际消费点 `BAI_v15.cpp:402` 将 LAB_BATTLEAI_TEACHER_TURNS 交给 BattleEvaluator，显式只允许2/4/10；3会抛错。本实验不修改native二进制，不伪称depth3。BattleExchangeVariant.cpp:714按simulationTurnsCount循环交换turn/完整单位队列，不能称完整minimax博弈树层数或精确规则穷举。CBattleAI默认另由游戏difficulty选择2或10，不能假定teacher与实际对手是同一个配置。

本目录从已验证runner复制，取消人工规则覆盖，只用原生teacher映射的合法action。记录每决策原生 teacher_action_description 中 teacher_eval_us，区分CPU搜索成本与Python选取耗时；没有CUDA/参数更新/强化学习训练。

首先单局 horizon4：原训练图0、attacker、seed2026101811，外部90秒上限，记录成功或失败/超时。若成本可用，跑2训练图×双方角色×两种子2026101811/12×horizon2/4，共16局。已跑的首局可复用，只按其完整SHA/正常终局核验跳过；不能把中断当胜利。

所有fixture来自此前明确使用的训练组，只比较训练阶段策略质量/搜索成本。原development/test保持未运行。主要对照是主力（swordsman id6）永久损失、总损失、胜负、真实选中动作差别；报告每单元与角色。2个训练场景无广泛泛化证明。4不优于2就保留失败，不自动扩到10，更不跑BC。

每局全局共享锁、单worker、独立工作目录、完整事件与终局，所有策略/地图/依赖SHA冻结，旧目录/模型不覆盖。更长模拟可能放大规则近似和目标错配，不能先验称更强教师。
