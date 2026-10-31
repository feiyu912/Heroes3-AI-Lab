# 实际 TRAIN 建造编码可辨识性检查

2026-10-20，仅 CPU 读取与编码审计；没有运行原生游戏、GPU、优化器或改变冻结训练输入。

## 结论

本批真实 2089 条 TRAIN 请求中，288 条提供建造候选，共 806 个建造候选。**没有发现同一请求内不同建筑候选的完整编码行逐位相同**，同城不同建筑的碰撞数同样为零。因此撤销“本批实际候选已存在建筑同编码碰撞”的假设，不据此增加模型参数或宣称修复能力缺口。

Tavern（BuildingID 5）在本批候选中出现 0 次，Marketplace（BuildingID 14）出现 96 次。已安装原始资源及 cap02 对应加载源码表明，两者基础价格均为木材 5、金币 500、其余资源 0，功能不同：酒馆包含士气及盗贼公会访问效果，市场提供资源交易权限。实际市场候选价格与该价格一致；本批没有酒馆与市场同时可选的真实请求，不能把基础价格相同当成实际编码碰撞证据。

## 观测字段的实际边界

冻结 schema5 encoder 校验 own_towns 的 buildings、faction_id，但不把它们输入网络；建筑 ID 也不作为候选特征。建造候选主要编码类别、七项成本及资源比例、动作类型。ID 仍用于实际动作绑定，不等同于网络能辨识它。

真实相邻观察中有 41 对城镇已建建筑集合发生变化，但完整编码也都发生变化，无法从这些观察隔离“已建建筑字段本身”的作用。另有一对不同对局的完整编码相同、城镇事实不同，但仅 town_id 不同，阵营与建筑集合相同，不构成建筑或阵营不可辨识的实际证据。

两个人工 CPU 反例分别仅修改建筑集合或阵营，其他字段与候选保持不变，完整编码不变。这只确认编码函数忽略这些字段；改动后的状态与候选没有经过原生合法性认证，不能称为真实游戏局面。

这些结论与单场 q4 回城选择的分岔不同。本次没有证明该观测缺口导致那场胜负，也没有使用 DEV 决策作为教师标签。

## 可复核证据

- `train-evidence-03/AUDIT.json`：正式实际请求审计；2460 项 admission/raw/source/runtime 输入 SHA 前后复核。
- `train-evidence-03/ROW_COLLISIONS.json`：空列表。
- `train-evidence-03/ACTUAL_BUILDING_CHANGES.json`：41 对实际建筑集合变化。
- `train-evidence-03/ACTUAL_COMPLETE_INPUT_COLLISIONS.json`：一对仅城镇 ID 不同的编码相同记录。
- `train-evidence-03/native-source/`：cap02 对应配置及 BuildingID 枚举快照。
- `cost-evidence-02/AUDIT.json`：只读 LOD 资源解析及编译加载源码绑定。H3bitmap.lod 与 H3ab_bmp.lod 的 BUILDING.TXT 内容相同，条目 SHA256 为 `3be629f3f16af234e005eeae7c4fb8a563db88cafb04baf2b3269eff934e1186`。原始第 110/119 行分别为酒馆/市场同一价格。
- `study_cpu.py`、`legacy_cost_cpu.py`：隔离复核脚本。早期 `train-evidence-01/02` 与 `cost-evidence-01` 保留 CPU 工具设置失败记录，未覆盖，也不计作原生游戏失败。

本轮未实现新 encoder、model、native epoch 或训练包。后续招募动作仅作字段评审，须等待明确的新原生契约与独立资格。
