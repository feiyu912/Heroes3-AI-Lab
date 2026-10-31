# MiniMax 校准方法顾问意见

实际路由 mini / MiniMax-M3.1-Flash；session session-892a677b-b1d5-4d35-96be-f144171ca6e0；4096 maxTokens / low reasoning / 零工具。输入仅实施者报告，未查看原始证据，非审计通过或执行授权。

1. **先设识别门**：同源模型、初始状态、地图与seed下并列CPU-argmax、CPU-multinomial、GPU-argmax、GPU-multinomial；核对logits、合法掩码、概率、dtype、确定性设置及RNG映射。GPU-argmax须先匹配CPU；GPU/CPU-multinomial用同一随机数流配对，排除设备、RNG与精度影响后，才比较“贪心校准”与“训练采样”。  
2. **最少证据**：每个决策记录状态/观测哈希、合法动作、全部logits或归一化概率、采样动作、奖励、下一状态哈希及首次分歧步；只在共同前缀内配对，分叉后各自成轨迹并按seed聚合。重复固定RNG流可检查经验分布，但不得新增训练seed、PPO、专家标签或DEV调参。  
3. **先验证分布，再谈兵量**：当前先完成既定实验；诊断仅能提供“采样会改变动作/前缀，且与校准推断不一致”的有限机制证据，不能证明隐藏因果、统计显著性、跨地图/seed泛化或训练收益，更不能宣称已4败或实验通过。
