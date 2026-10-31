# Decision Model与真实战斗结果

2026-10-14。共享实体编码＋动态候选评分＋可训练Value头；已完成真实BattleAI数据→BC→checkpoint重载→实际VCMI执行→Masked PPO→独立评测。

| BC模型 | 参数量 | 测试Teacher Top-1 | 独立战斗胜率 |
|---|---:|---:|---:|
| mlp | 144,514 | 63.3% | 26.9% |
| attention | 409,474 | 66.2% | 36.2% |
| gnn | 210,306 | 63.4% | 30.0% |
| mlp64 | 43,586 | 61.0% | 34.4% |
| mlp-no-value | 111,489 | 63.0% | 26.2% |

BC用同一课程/种子20261014，width128（小模型消融64）、12epoch/batch64/Adam3e-4/梯度裁剪1.0；以验证CE挑checkpoint。MLP池化、两层Attention、两层普通GNN实测；无需LLM/JSON token输出。无Value头变体真实去掉该头，比较的是BC，不把无critic训练冒充Actor-Critic PPO。

所有网络共享v15编码，输出只对引擎合法候选归一化，padding概率0；空集合在非终局被拒绝。Action ID只在当前状态内有效。实体输入和候选关系复用引擎规则，不重新写伤害算法。模型输入缺口详见STATE_INTERFACE_AUDIT.md：当前没有逐堆原始HP/数量/攻防速、稳定兵种ID和英雄施法状态；GNN丢弃部分边类型/属性；不能说完整英雄/战术状态已经实现。

同一held-out160场测试：原BattleAI对自身50%，启发式10.625%、随机合法1.25%。纯BC-GNN30%；三个独立PPO种子分别47.5%、53.125%、65%，均提高对应BC，平均55.2083%。同时重采训练种子与场景的bootstrap均值95%区间约42.3–71.3%，比BC改善的区间约+7.7–46.9个百分点，不能将最高65%当作稳定总体胜率。BC+PPO-MLP52.5%、Attention35%，后者本次单seed没有收益，不默认更大网络更强。

当前按验证集胜率、再按同场景真实损失数量打破平分选中 `ppo-balanced-rollout64`（GNN21万参数）；不是按test挑65%模型。该候选held-out160场胜率55.0%，Wilson95%47.3–62.5%，非法动作0、截断0。vs StupidAI80场75%；vs随机合法80场72胜/8回合限制截断，总体90%，没有把72/72当100%。这个失败说明跨对手稳定性还不充分，不宣称全面超过BattleAI。

失败复现：随机对手的8截断集中在balanced-29/35（枯木卫士/弓箭手/狮鹫）；都射击12次，之后大量等待/移动。random-failure-diagnostic-29.json确认末局无弹药、双方仅剩地面单位、非终局而到30回合限制。不能证明无限死循环，但足以定位弹药耗尽后的进攻/追击课程不足。混合对手训练对随机对手95%、4截断，却把BattleAI测试降到39.375%；对手比例/难度要重新设计。

主要指标均为实际战斗胜数/总局数，不是Policy softmax或Value输出。Value预测折扣奖励，不能直接称胜率。每模型test为10场景×双侧×8引擎seed，battle均新进程；validation是另外6场景×双侧×4seed。测试场景军队数量/部署未用于训练，但同一固定平原和熟悉兵种，不能推广到攻城/魔法/全图。置信区间与逐场配对结果在research/GOAL_RESULTS.json。

GPU已接入真实训练和推理；当前执行路径仍是Python/PyTorch→v15合法动作→VCMI，未导出ONNX/C++产品部署。可读模型备份在models/selected-v3，训练器原模型在WSL。源代码为battle_features.py、decision_model.py、train-bc.py、masked_ppo.py、vector_env.py、train-ppo.py和评测脚本。
