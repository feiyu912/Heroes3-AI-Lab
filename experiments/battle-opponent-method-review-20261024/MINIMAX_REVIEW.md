# MiniMax 基于摘录的方法审查

实际路由 mini / MiniMax-M3.1-Flash；session session-a2cfea51-3810-40fb-8766-2566046c6516；4096 maxTokens / low reasoning / 零工具。仅看到TASK.md最小摘录和本地调查者证书汇总，非独立原raw审计。

**审查结论：**  
1. **“对公开作者MMAI训练”已部分实现**：16槽中8槽为 `MMAI_MODEL`，使用作者公开 ONNX，角色互换、temperature=0、CPU执行；因此不是尚未开始的新方向，而是现行50:50混合条件。公开来源与冻结字节相符；但当前C++ factory不属历史freeze，不能据其SHA重建历史binary。  
2. 若将BattleAI槽全改为原CPU MMAI，在同16槽、地图、角色、steps/quota及全部学习器状态不变下，可称为**单一“对手分配”处理包**；即使效果改善，也只能归因于该分配组合，不能先验保证提升，更不能归因于terminal信用、模型质量或GPU。DEV中candidate不劣于control的失败不具候选特异性，不能用于选型。  
3. **必要门**：两臂角色/地图/种子/预算严格配对；MMAI权重、温度、CPU后端和动作接口完全相同；不得把MMAI动作作专家标签；采样配额、终止规则及角色可用动作空间一致；记录每环境CPU时间、episode长度、轨迹量、截断/超时及有效样本量，避免CPU资源或数据量成为隐藏处理。  
4. 报告应同时给配对胜率及不确定性、episode长度/步数分布、CPU墙钟与样本吞吐，按对手类型分层，并声明失败模式。  
5. **仅先做TRAIN内失败诊断**：对现有DEV/TRAIN日志按角色、地图、终止原因、剩余步数、超时和动作合法性分层，核对MMAI/BattleAI及反事实胜负；不得用DEV挑对手/超参，不触final test，也不授权新实验。
