# GPU与完整训练实测

2026-10-14。本轮全部正式训练固定12环境，中央GPU推理/更新，游戏规则模拟仍由CPU运行。

| 对照 | 采样步 | 更新次数 | 验证胜率48场 | 测试胜率160场 | 正常终局平均损失单位数 |
|---|---:|---:|---:|---:|---:|
| ppo-balanced-seed-20261014 | 98,304 | 256 | 50.0% | 47.5% | 84.97 |
| ppo-balanced-seed-20261015 | 98,304 | 256 | 52.1% | 53.1% | 81.74 |
| ppo-balanced-seed-20261016 | 98,304 | 256 | 60.4% | 65.0% | 79.27 |
| ppo-balanced-shaped | 98,304 | 256 | 60.4% | 58.8% | 82.97 |
| ppo-balanced-mixed | 98,304 | 256 | 47.9% | 39.4% | 85.60 |
| ppo-balanced-rollout64 | 98,304 | 128 | 60.4% | 55.0% | 84.63 |
| ppo-balanced-batch128 | 98,304 | 256 | 35.4% | 37.5% | 87.39 |
| ppo-balanced-epoch1 | 98,304 | 256 | 47.9% | 48.1% | 86.01 |
| ppo-balanced-mlp | 98,304 | 256 | 56.2% | 52.5% | 84.96 |
| ppo-balanced-attention | 98,304 | 256 | 41.7% | 35.0% | 90.01 |

十组每组98,304步，合计983,040步。3个独立训练种子、终局战损率塑形、混合对手、rollout32/64、batch64/128、epoch3/1及MLP/Attention/GNN均实际运行；各自保持同采样预算。混合对手为BattleAI/StupidAI/随机合法各1/3。所有有效正式训练退出正常，损失/梯度有限，掩码与旧log-prob重算通过。最大训练PSS采样峰值5.63GiB，GPU分配峰值257.2MiB（不含全部CUDA上下文/桌面显示）。训练中总计9次回合限制截断，正确bootstrap最终状态并切断GAE；不是全部episode都到真实胜负。

CPU/GPU完整配置网格见research/training-device-grid-fixed.json：4/8/12/16/20环境 × CPU/CPU、CPU/GPU、GPU/GPU ×2重复，每点6次PPO更新，去掉首个更新后统计稳态。所有worker同一20对10弓箭手场景/攻击侧/初始BC-MLP、相同规则与种子前缀；rollout32/batch64/epoch3，精确合法动作、真实模型推理、采样及更新全部包含。不同设备的随机采样序列可能不同，所以固定的是场景与预算，而不是跨设备逐帧完全相同。两次范围和完整含初始化指标均保留，不挑最好一次。最早的training-device-grid.json混合场景分布随并行数改变，仅作为探索性数据；不能直接据此认定跨并行数优劣。

| 固定场景12环境 | 稳态steps/s中位数 | 两次范围 | PSS采样峰值GiB |
|---|---:|---:|---:|
| cpu推理/cpu更新 | 381.3 | 366.7–395.9 | 4.30 |
| cpu推理/cuda更新 | 488.3 | 473.5–503.1 | 5.46 |
| cuda推理/cuda更新 | 469.0 | 463.0–475.1 | 5.47 |

固定简单MLP场景的CPU推理/GPU更新略快；多兵种GNN/Attention的网络计算更重，本轮采用GPU推理和更新。Windows同版本/同真实输入网络微基准为model-device-benchmark-windows.json：小MLP批1/12的CPU推理更快，训练batch64的GPU明显更快。微基准包含数据传输、5次预热/20测量；不能把它代替WSL完整训练速度。

可变候选batching已比较：padding-benchmark.json，对同1024个真实验证状态，随机padding与按候选数量分组，32/64/128/256batch、3重复，含排序、装配、传输和GPU推理。分组减少padding，但这里只测离线推理；不能宣称PPO学习质量或更新速度必然改善。首重复有冷启动，查看中位数和后续重复。

优化：模拟worker不再导入Torch/CUDA（12个worker均验证false）；抽出NumPy-only battle_features.py。缓存next Value避免重复前向，两个独立实际运行的action及GAE return hash完全一致。原v15接收max_steps但不执行该上限；已在vector_env增加显式step cap，并用真实一回合测试验证final observation与reset observation分开。实际Gym回合上限为30，wrapper默认step cap400，通常先到回合上限。

Masked PPO配置：gamma.99、GAE lambda.95、clip.2、entropy.01、value系数.5、梯度裁剪.5、KL阈值.03、Adam1e-4。纯胜负普通步0/正常终局±1；塑形仅终局小权重.05×(敌我真实伤亡数量比例差)，仅限无复活/召唤课程，不当作兵种价值或跨地图最优奖励。

GPU测温/占用每16更新采样，全部在保护限内。WSL可用内存2GiB/Swap256MiB保护，出现异常/超时/过多截断会停止。core-type-telemetry.json读取Windows CPU-set：16逻辑线程较高效率等级、12较低等级，与8P+12E结构吻合；采样平均利用率约34.6%/16.9%，包括主机后台负载，不是训练进程专用数据。微软说明较高EfficiencyClass通常更快但功耗效率较低：[接口定义](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-system_cpu_set_information)。WSL虚拟编号没有可验证的主机核映射，没有伪造P/E绑核结论；CPU实时温度/频率仍无可靠传感器。

每次更新保存latest/优化器/进度，周期策略快照保留。新checkpoint还保存CPU和CUDA RNG；早期checkpoint只存CPU RNG，恢复不等于原战斗逐帧继续。所有环境会以记录seed重新创建。resume-gpu-probe.json已验证恢复128更新的选定模型并继续GPU更新、正常退出。RUN_TRAINING.ps1默认GPU、12环境、正确v2课程，先续训再做验证集战斗检查；后台没有无上限训练器。
