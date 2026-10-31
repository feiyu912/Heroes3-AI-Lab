# 本地战略候选策略与文件 broker

此目录独立于旧战斗模型。它只读取 C++ 依据合法可见观测生成的候选，从中选择下标；自动建设/招募仍由当前战略启发式执行。不是 LLM，也没有读取引擎隐藏地图。

## 可运行接口

WSL 中的现有 Python 环境即可，不安装依赖或调用联网服务。heuristic 模式只用标准库；policy 模式使用本机 torch，当前推断明确为 CPU。

```text
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/smoke_game.py --map Maps/adv/takeover-v2-train-01-mines --seed 2026101821 --seconds 120
```

该命令会真正启动一次游戏：创建唯一空 agent-dir，先启动 broker 等 ready，再调用主 runner 的 `--agent-dir`；资源锁由主 runner 获取。输入/输出、broker/runner 日志、smoke-plan 与结果均留在打印的唯一目录。实现与合成自检没有自行运行这条命令；主窗口已另行实测 heuristic 全局闭环。

使用已初始化、尚未训练的 prior 策略：

```text
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/smoke_game.py --mode policy --checkpoint /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/checkpoints/prior-initial-v2.pt --map Maps/adv/takeover-v2-train-01-mines --tag strategic-prior-smoke-v2
```

只启动 broker、不启动游戏：

```text
python3 /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/broker.py --agent-dir /本局唯一空目录 --mode heuristic
```

## 协议

C++ 原子写 `request-%08d.json`，schema 为 `strategy-candidates-v2`，内含相同的正整数 request_id。状态字段：player/day/hero/from/gold/wood/ore/own_army_value/movement。candidate 字段：kind、position、next、path_cost、heuristic_score。坐标可为 `[x,y,z]` 或 `{x,y,z}`。kind=0敌英雄、1敌城、2矿山、3拾取、4补给、5探索边缘。

broker 返回同 ID 的 `action-%08d.json`，内容为纯整数候选下标及换行。先 fsync 决策审计，再临时文件 fsync + rename 发布响应；记录输入/输出 SHA、ID、候选数、player/day/hero、策略版本、代码 SHA。单局 broker 使用非阻塞独占文件锁；重复目录与已有响应作为错误处理，不盲目复用旧决策。

无候选、非法 kind、非有限数值或 ID 不匹配不会产生 action；记录 error 文件与审计。C++ 负责最终范围/路径校验，并在超时后失败结束，不能默默执行旧动作。文件协议不等于引擎内部精确恢复协议。

## 编码和模型版本

`encoder.encode(request)` 返回 11 维可见状态与每候选 15 维特征；kind one-hot、目标/下一步相对坐标、路径成本、压缩启发分数等。`collate(requests,device)` 返回 state/candidates/mask，批内按候选数 padding。`model.forward` 返回 masked logits 与未校准 value；非法 padding 为 -inf，padding 中的 NaN 被清除后才参与网络。value 不是胜率。

第一版随机 actor-critic 源文件及 CPU 结果已保留在 `versions/baseline-v1/`；原 `CPU_SELFCHECK.json` 不覆盖。

新模型 format 为 `strategic-candidate-prior-residual-v2`：

```text
logit = 64 × candidates[...,13] + trainable_residual
candidates[...,13] = tanh(heuristic_score / 100)
```

11906 个可训练参数；固定正 prior scale=64，actor 隐层正常随机初始化，仅最终残差权重/bias 为0。critic 正常随机初始化，未校准。checkpoint 同时保存 format、encoder版本、prior 配置与state_dict；旧v1 checkpoint仍能按旧结构加载。

`checkpoints/prior-initial-v2.pt` SHA 为 `8dd2cc8eeb09c2e83421fd0ec6c2958ba64716580e2dac74086bbb8d92f7e5d3`。它是**显式启发式初始化，训练更新数0**。实际已采集的242份请求全部CPU检查：初始模型 argmax 与启发式 argmax 242/242一致。数值范围内的单调变换不等于浮点数永远不合并近似分数，极端值或极近分数的次序应继续审计。

## 已做与未做

`CPU_SELFCHECK_v2.json` 是实际运行的合成 CPU 自检：变长mask、合法选择、NaN padding、候选置换等变、正 prior/负分排序、随机隐层+零输出层、actor/critic有限梯度，以及两个合法文件请求和一个非法请求不回动作。只做一次合成 backward，没有优化器训练、没有CUDA learner、没有自启动游戏。

`ppo-pilot-02` 已在 GPU 完成两次实际 PPO 更新、176 次 Adam step，保存 `update-1.pt` 与 `update-2.pt`。8 个正常训练对局对 EmptyAI 4 胜、对 Nullkiller2 4 负；第三轮第一局超时，invalid 且 reward=null，未更新。训练成绩不能证明独立能力提升。尚无战略 BC 学习收益或通过总体收益认证的战术专家课程。

当前 trainer 提供 `--resume`（相同协议、完整 update 边界，目标 `--updates` 是总次数）和 `--initialize-from`（显式仅迁移权重，重置 optimizer、update 和 RNG，记录 parent SHA）。二者互斥；旧协议 `ppo-pilot-02/update-2.pt` 应通过后者迁移，不能伪称原协议续训。改代码、运行时或地图会改变冻结协议；必须使用新输出目录。

checkpoint 原子保存，恢复的 SHA、权重、optimizer 和 RNG 来自同一次文件读取；逐 update 独立记录 actor/critic 参数变化，失败后从 Adam 状态记录实际 step。失败中的 partial checkpoint 明确禁止 resume。CPU `--preflight` 不恢复或采集 CUDA RNG，不启动游戏、不执行 optimizer step。`audit_checkpoint_cpu.py --out <新目录>` 可复现合成 CPU 保存/恢复、故障注入和连续两次更新与边界恢复逐位对照；这不代表真实游戏恢复或独立胜率已通过。真实游戏边界续训及未见地图配对评估仍需新冻结实验。
