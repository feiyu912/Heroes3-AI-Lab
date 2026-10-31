# 真实训练边界对照工具与配对评估复核

本次未运行游戏、GPU 或 learner。只生成准备计划，执行带 `SYNTHETIC_ONLY` 标记的 CPU 夹具，以及一个用于验证进程清理的普通 CPU 父子进程。历史训练、冻结模型与 trainer 均未修改。

## 边界恢复工具

`verify_training_boundary.py` 默认仅生成新唯一目录中的冻结计划，不启动训练。必须显式 `--execute` 才顺序运行：

1. 从旧 update-2 显式仅迁移权重，连续跑至新协议 update 2，共 8 个课程对局。
2. 从同一旧文件再次显式仅迁移权重，跑至新协议 update 1，共 4 局。
3. 相同协议 `--resume` 第二步的完整 update-1，目标总 update 数 2，只跑接下来的 4 局。

共 16 个训练课程对局；唯一 learner 逐阶段串行，trainer 独占 GPU 锁，runner 遵守共享模拟锁。每阶段验证代码、原生运行时、DirectorAI 源码、配置、训练地图与 parent checkpoint 的冻结 SHA；检测修改即中止。`--compare-root` 可对已完成的 root 重新生成比较报告，不启动训练。

比较连续/分段的 update 1、连续/resume 的 update 2：权重、Adam state、CPU/CUDA/Python RNG、完整边界标记、实际 step 数与协议内容；校验 resume parent SHA。逐局比较配置、合法有效终局、奖励、移动数、完整 rollout 请求/动作/logp/value 与 native 决策 JSONL。序列化文件 SHA 因 lineage/输出 plan 不同可不同，不以文件字节相等代替语义参数比较。报告保留 trainer 的逐次 actor/critic delta 和实际步数。

每约一秒采样整棵 owned 进程树 RSS、设备 GPU 内存与利用率。RSS 包含重复共享页，GPU 数字为设备总量，明确不能归因于 learner。异常/超时或正常退出后发现残留 owned 进程，依据 PID+starttime 清理，包括独立 session；异常写 failed 报告，不继续下一 learner。

执行入口（待主窗口诊断完成后冻结再运行，必须使用新目录）：

```text
wsl -d Ubuntu-22.04 -- /root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/verify_training_boundary.py --out /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/native-boundary-new --execute
```

默认 parent 为 `ppo-pilot-02/update-2.pt`，可用 `--initialize-from` 指定其他显式迁移 parent。默认每阶段墙钟预算 1800 秒。未传 `--execute` 只准备计划；现有 `boundary-harness-prepared-20261018/` 是较早源码快照的 prepare 证据，不应当作运行结果。

## evaluate_pairs.py 审查与修复

原脚本的同地图/种子/角色/对手 CPU argmax 开发集配对设计合理，未触 test split，不能据此认证最终泛化。发现并修复：

- 原异常会遗留 `status=running`；现在异常原子写 failed，invalid 的 win 为 null，不补负局。
- 增加 ready checkpoint SHA 校验、broker 到 native 逐请求 action/目标/下一步与 player/day/hero/from 对齐；只有 broker 文件完整还不足以证明原生实际消费。
- 校验原生实际 AI 分配、合法胜方和 inputs_unchanged；输入变化会使当前结果 invalid。
- 增加 DirectorAI 源码及原生 config 冻结与源码快照。原生主要三个 runtime 文件仍冻结；依赖的整套第三方游戏资产不在本工具逐文件 hash 范围。
- baseline/candidate 首跑顺序按配对交叉，聚合按模型名而非旧固定行位置。输出 discordant pairs 和对手×角色统计，保留开发集聚类/小样本限制。
- `--seeds` 限为 1..100，使用不重叠地图/对手 seed 段，避免旧 seed 公式在增加 seed 数后碰撞。

evaluate_pairs SHA：`a95fca92a27239fee0d0efc42832beeb9e93a9a8d59747c00cfd7457ab995a1c`。

## CPU 实测证据

`recovery-tools-cpu-audit-20261018-v2/AUDIT.json`，含精确 `sources/` 快照。`audit_recovery_tools_cpu.py` 仅 mock 游戏 subprocess，输出全部置于有 `SYNTHETIC_ONLY.txt` 明示的审计目录，不是原生胜率证据。

- 8 对合成夹具验证交叉首跑顺序及配对聚合。
- 故意错配 native action，评估立即 failed，valid=false、win=null。
- 合成 checkpoint/逐局轨迹相等时通过；改 actor 权重或 native 动作后分别检出差异。
- 冻结输入被改变时拒绝继续。
- 实际启动普通 CPU 父子进程，子进程自行新建 session；父进程退出后检测残留子进程并清理，survivors 为空，没有进入下一阶段。

工具复现：

```text
wsl -d Ubuntu-22.04 -- /root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/audit_recovery_tools_cpu.py --out /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/recovery-tools-cpu-audit-new
```

边界工具当前 SHA：`7df6737306610111ff57a46d168bcc1046b572ab8f3d276184abe90fc73da42c`。真实 CUDA/原生边界一致性、设备资源值与开发能力成绩均待主窗口运行，本报告不提前认证。
