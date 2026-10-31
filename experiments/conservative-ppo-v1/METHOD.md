# 保留公开策略的 Reference PPO

2026-10-16。此目录只实现可选参考策略约束和CPU数学检查，没有启动游戏、GPU或新训练，尚无胜率收益证据。原research及Human pilot Python未修改。

## 动机与边界

根任务独立512局已见选定候选434胜（84.77%），公开策略457胜（89.26%）；守方215胜对237胜回退22局。结果说明原训练未达到目标，不能用开发集的高分宣称成功。下一路线应控制偏离公开策略，并使用扩大的48开发场景选模型；已读512局转为诊断，不能继续作干净的模型选择或最终确认集。

本模块加入KL(reference || learner)，但约束可能阻碍有益改进，也不能保证不遗忘。计划中的public initial-pair、heads-only、低学习率1e-5、reference_coef0.1、gamma1、stepcost0、shaping0.5、24workers、先32updates是一组新路线参数；不是已经训练有效，也不是原路线的单变量消融。实际配置、数据、模型SHA及未见确认集由trainer另行冻结。

## 数学实现

复用research/masked_ppo.py的GAE和合法Categorical分布。保留优势标准化、PPO裁剪目标、0.5值函数MSE、熵项、梯度裁剪0.5、旧策略近似KL提前停止。新增目标为：

`loss = original_ppo_loss + reference_coef * mean_s sum_legal_a p_ref(a|s) * (logp_ref(a|s) - logp_learner(a|s))`

参考分布必须为每个观测完整合法候选的归一化log概率，不是只给采样动作概率或教师argmax。每行先用mask取合法项再相乘，从不对非法padding计算0乘负无穷；合法logits/logp必须有限，空mask拒绝。参考logp内部detach，引用参数须冻结且与learner/optimizer均不相交。

重算必须显式传原rollout推理批量（当前计划24），在任何optimizer更新前，按相同样本顺序/候选/mask/批量重算所有旧logp。绝对容差至多2e-4、相对容差0；不因参考项而放宽。所有参考行的长度与归一化也在更新前检查。非法候选、错误对齐或数值不一致直接停止，不能通过截断/重置优化器掩盖。

## 接口

```python
reference.eval()
for parameter in reference.parameters():
    parameter.requires_grad_(False)

ref = encode_reference(reference, raw_observations,
                       collate_fn=graph.head_collate, batch_size=24)

metrics = update(
    learner, optimizer, learner_cached_features, actions,
    old_logp, old_values, advantages, returns,
    collate_fn=graph.head_collate, recompute_batch_size=24,
    recompute_atol=2e-4, recompute_rtol=0.,
    reference_log_probs=ref['log_probs'],
    reference_action_ids=ref['action_ids'],
    candidate_action_ids=[list(obs['active_action_ids']) for obs in raw_observations],
    reference_parameters=tuple(reference.parameters()), reference_coef=.1)
```

`encode_reference`只接原始obs，调用reference自身encode_features与head_collate。返回dict：log_probs（逐obs的CPU Tensor合法行）、action_ids（逐obs有序ID列表）、encoding_batch_size、provenance。即使当前heads-only且body起初相同，也独立编码；以后body不同时不把learner embedding错误喂给reference。不能将对手视角obs替代当前学习器视角obs。

候选ID必须与learner缓存来自同一原始观测且完全同顺序。模块校验双方ID列表及概率长度；调用方仍须保证传入列表确实对应缓存而非自造。缓存只在冻结body和对应特征版本下有效，改变body后必须重新编码。

reference_coef=0时不读取参考分布、不增加目标，要求相同重算阈值/批量以便与原PPO精确对比。新增metrics.reference_kl为有约束时的更新前参考KL均值；coef0时为0，不表示实际策略距离一定为0。approximate_kl仍是旧rollout策略的PPO约束，二者不同。

## CPU实际检查

```bash
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/conservative-ppo-v1/check_reference_ppo.py
```

结果见cpu-math-check.json，全部通过：

- coef0与原PPO逐参数bitwise相同，共有metrics数值完全相同。
- 偏离参考时KL为1.404219，沿负梯度一步降至1.298570；reference梯度为None。
- 非法padding为NaN、正/负无穷或极大logit时，合法KL/梯度不变，非法梯度为0。
- 不同body的reference确实独立重编码原obs，结果不等于借用learner缓存。
- cached-feature PPO更新有限、reference参数不变，旧logp按3/3/1原批量重算，误差0。
- 超过2e-4、放宽阈值、相对容差、候选错序、参考混入optimizer、参考长度错误均在修改learner前拒绝。
- 空mask、合法NaN拒绝；GAE在truncated时bootstrap但停止跨episode递推。

这些是合成CPU数学证据，不等于24并发CUDA、原生退出或胜率验证。根trainer仍须跑真实观测契约、同批量CUDA重算、存档恢复、固定公开对手一致性与普通能力回归；最终目标需要冻结模型后的新独立确认集。
