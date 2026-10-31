# Decision Model最小闭环

日期：2026-10-14。已完成真实教师采集→BC→验证选checkpoint→重新加载→真实战斗执行。

| 模型 | 参数量 | 初始验证Top-1 | BC验证Top-1 | 测试Top-1 | 测试Top-3 | 测试masked CE | 最佳epoch | 训练秒 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| mlp | 144,514 | 27.1% | 52.9% | 49.2% | 72.7% | 1.836 | 3 | 18.4 |
| attention | 409,474 | 14.4% | 51.9% | 43.2% | 72.6% | 1.747 | 2 | 99.1 |
| gnn | 210,306 | 5.4% | 48.9% | 43.9% | 72.7% | 1.804 | 3 | 34.9 |

三模型使用同一数据、seed20261014、width128、16epochs、batch32、Adam3e-4、梯度裁剪1.0；按验证masked CE选择checkpoint。单次训练seed和很小的场景集不足以给架构排名置信区间。Value以同场教师轨迹的终局+1/-1监督，权重0.1；不是动作胜率。

公共输入为v15 Global/Player/Unit/Hex实体，各类型padding到35维并加类型编码。候选特征包含原始动作编码、执行单位、落点、目标、阻挡单位及引擎关系伤害属性。状态只编码一次。MLP池化、两层attention和两层普通图消息传递对照；无需torch-geometric。实体pooling与候选共享评分，Policy给合法候选logits，Value评估局面。Mask仅由引擎合法候选生成，padding概率为0。没有用非法动作惩罚代替规则mask。

本轮PPO先接小型MLP，便于控制CPU推理成本；GNN验证CE略好、MLP教师Top-1较好，复杂网络尚无足够实际收益证据。三模型保存/重载得分完全一致；合批padding不改变单个局面输出、候选重排对应重排logits、只采合法动作的测试通过。

真实对战：两个完全未见训练场景、攻守两侧、每侧5个独立引擎seed。BattleAI教师、诊断启发式、BC-MLP和BC-attention各20场，全部正常结束且非法动作0。各自胜率均50%，Wilson95%约[29.9%,70.1%]。这组测试兵力差异较大，胜率敏感性不足，不能宣布模型等于或超过BattleAI。平均永久损失单位数：教师20.70、启发式24.05、BC-MLP24.70、BC-attention24.95；不同兵种不能仅用数量汇总比较价值。保留逐场结果供分析。

代码：research/decision_model.py、train-bc.py、evaluate-policy.py、evaluate-battles.py、test-training-contracts.py。checkpoint在 /root/heroes3-ai-lab/models/bc-v1/{mlp,attention,gnn}.pt；参数、数据manifest hash和训练信息嵌入checkpoint，文件hash在research/bc-baseline-v1.json。当前部署是Python/PyTorch通过合法VCMI动作接口，尚未导出ONNX或原生C++推理。

缺口：DEFEND教师监督、障碍/攻城/主动魔法、复杂永久战损、丰富的均衡测试场景；当前编码复用v15，尚未补全兵种ID和特殊技能原始属性。改进搜索教师尚未实测。先扩数据和公平评测，再根据证据升级网络。
