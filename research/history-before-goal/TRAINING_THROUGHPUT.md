# 12环境端到端训练实测

日期：2026-10-14。用户指定12环境，本轮固定此配置，未重新进行4/8/16/20全训练配置搜索。

| 实验 | 并行环境 | 采样步数 | 更新次数 | 训练墙钟秒（不含启动/关闭） | 端到端steps/s | PSS采样峰值GiB |
|---|---:|---:|---:|---:|---:|---:|
| 短程验证 | 12 | 3072 | 8 | 12.81 | 239.8 | 5.46 |
| 续训pilot | 12 | 24576 | 64 | 100.60 | 244.3 | 5.52 |

算法：BC初始化Masked PPO，Actor/Critic、GAE(gamma0.99,lambda0.95)、优势归一化、clip0.2、entropy0.01、value系数0.5、梯度裁剪0.5、KL阈值0.03，Adam1e-4。每次rollout32×12=384步、batch64、最多3epochs。采样与更新使用同一份保存的候选顺序/掩码；每次更新前重算log-prob并校验与采样值一致。

只用权威正常终局胜负+1/-1，普通步0；不使用旧Gym伤害奖励或未经验证的永久战损塑形。terminated不bootstrap；truncated bootstrap最终状态且切断GAE，不连接下一episode；相应测试通过。Value/梯度/概率检查有限值。

12个独立VCMI进程，各有独立资源/日志目录；中央训练器批量CPU推理和更新。仿真、特征抽取和IPC时间会重叠，记录的environment_ipc_seconds是父进程等待墙钟，不能拆成纯引擎开销。每步当前实现还单独推理next value，后续可缓存以省开销。所有worker带Torch模块依赖，增加内存；后续可把轻量特征抽取与Torch解耦。

纯环境约1011 decisions/s与这里约240–260 steps/s负载不同：训练是多兵种课程，另有特征/IPC、Policy推理、bootstrap及PPO更新。不能把差距全部归因于模型。GPU未参与，没有GPU推理/更新速度、显存或CPU-vs-GPU对照结论；小型网络先CPU闭环，后续按同负载比较。

短程474场战斗、续训3963场，均未出现截断；12进程全部exit0。续训采样到最低WSL可用内存9.48GiB，Swap峰值0MiB。PSS含父训练器和12个worker，采样未覆盖所有瞬时峰值。Windows内存/CPU时间序列在research/windows-training-telemetry.json；CPU温度与P/E核型监控尚不可用，不能宣称通过温度压力验收。

已经完成8+64=72次优化更新、3072+24576=27648采样步。续训恢复optimizer与PyTorch RNG，但环境以保存seed重新启动；不宣称从中断战斗逐字节恢复。每次更新保存latest，续训每16次保存独立策略快照。pilot最终checkpoint：`/root/heroes3-ai-lab/models/ppo-1791979708445434633/latest.pt`。训练胜率来自固定课程，不能当独立测试胜率。

证据：research/ppo-short-v1.json、ppo-pilot-v1.json、training-contract-tests.json；代码为vector_env.py、masked_ppo.py、train-ppo.py。资源保护：可用内存2GiB、Swap256MiB、持续异常/worker超时或明显增加的截断会失败并清理进程。不留后台无上限训练器。
