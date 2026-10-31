# 战术知识记录契约

知识记录与动作轨迹分别保存。`source_wait_case.json`是已填写的来源知识实例；运行结果另存审计文件，不回写已被实验冻结的原始记录。状态以对应执行证据为准，原记录中的pending表示提取时状态。

每条知识记录需要以下字段，无法确认的值写null，并列入unknowns：

| 字段 | 内容 |
|---|---|
| case_id / schema_version | 稳定战术编号、记录格式版本 |
| source_id / source | 注册目录ID、作者、链接、日期、资料类型、版本、实际访问范围、权限与版权说明 |
| evidence_locator | 章节、段落、时间位置或存档/回放帧；没有视频证据不能填推测时间 |
| name / goal | 战术名称和要改善的可测目标 |
| preconditions | 地形、兵种、数量、速度、站位、行动权等适用条件 |
| key_mechanics | 所依赖的游戏规则、原文机制主张与本地实现位置 |
| operation_order | 合法操作顺序；抽象建议不能冒充动作ID |
| success_reason | 可检验的收益机制 |
| failure_conditions | 失效、无收益、反效果条件 |
| offense / defense | 主动使用方法、识别与反制方法，分别标记待验证或已验证 |
| opponent_responses | 可能应对及证据；工程假设与原作者实际观察分开 |
| rules_version | Complete/SoD/HotA/VCMI版本、规则、地图限制，未知项显式列出 |
| scope | 当前v15可执行、需主动法术、战略接口延期或暂不支持 |
| exploit_class | 针对特定旧AI缺陷 / 通用策略 / 待判定，并记录对手版本 |
| unknowns / reconstruction_disclosure | 原视频/教程未确认状态，以及本实验新建的兵力、位置和种子 |
| confidence | 来源解释、规则等价、复现成功、动作收益、模型学习五个维度，禁止用单一高分掩盖待验证项 |
| evidence | 规则检查、场景和源码SHA、正常终局、配对对照、反制、随机变体、BC前后、普通战斗回退的报告路径和SHA |
| split_definition | 按场景族/参数组划分train/development/test，冻结时间与定义SHA，模型选择是否使用过结果 |
| limitations | 混杂因素、未支持机制、权利边界、可迁移性限制 |

每次实际实验另生成不可混淆的结果记录：case_id、run_id、规则/代码/地图/模型SHA、种子、角色、合法动作、原始结算与审计、对照策略、收益单位、置信区间（若样本足够）、失败及无收益局。知识为真不等于当前重建忠实，也不等于训练标签最优。

动作数据使用 `expert_demonstration_schema.json` 与 `DEMONSTRATION_INGESTION.md`。来源支持的实验重建必须标记experimental_reconstruction；只有直接取得并校验的真人结构化操作可以标记human_recorded。模型训练与独立测试完成前，trained_model_benefit保持pending。
