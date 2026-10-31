# 顾问意见适用范围

这是一条真实MiniMax最终回答（单次请求），只看TASK.md中的实施者报告，未审source/model/原生日志。它不授权执行、不决定cell数或增加seed，不改变本轮训练/24DEV计划。

有用建议：先固定模型和×4地图/四新seed，区分设备数值/精度、mask/probability与决策规则；共同前缀记录state/obs/mask/logits/probability/RNG/selected action与首次分歧，分叉后独立轨迹；先验证采样分布再调兵量，结论不能直接变为训练收益。

需主代理裁量：
- 模型建议CPU/GPU×argmax/multinomial四组合，可用同状态离线回放比较补充设备/数值识别；并非必须擅自新增四组原生实验。原生cell数量必须另按冻结预注册准确登记。
- CPU/GPU相同seed不保证库实现同随机数流；必须检查实际uniform/采样实现或记录实际随机数、算法与概率，不可把“seed相同”当作RNG对齐证据。
- “GPU-argmax先匹配CPU”需预先给数值容差、近tie规则与动作一致性指标，不能事后筛掉不一致状态/负例。
- “重复固定RNG流检查经验分布”不能指重复同一seed同一draw当作独立样本；固定uniform网格/冻结draws可作确定性分布机制检查，不能擅自追加原生seed或推断总体胜率。
- 跨决策规则的首次分歧之后，不应再逐步相减声称同状态因果。
