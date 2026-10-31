# 原生 Ubuntu：零更新完整 learner 恢复资格（尚未运行）

入口 `qualify.py` 是 worker，root controller 负责按 GPU→pool 顺序取得非阻塞锁、传入真实 FD 及 device/inode 元数据，建立独立进程组并清理。worker 不创建替代锁。它先验证继承 lease 和新 Python profile 的 41 包 RECORD 证书，然后才 import Torch；GPU 初始化发生在这些门之后。

环境必须为 `native-gpu-verified-20261025` 的已通过全量 RECORD 检查实例。`--profile-certificate` 的 `environment_root` 必须等于实际 Python `sys.prefix`，证书、原详细 AUDIT 和 FILE_RESULTS 的哈希全部绑定。证书未通过则拒绝启动恢复。

`restore_learner_ubuntu.py` 从历史冻结 helper 逐字节派生，仅添加 os、把模块 ROOT 定位到 `HEROES3_PROJECT_ROOT` 的物理路径、查源时使用原 checkpoint 中 `/mnt/g/Heroes3-AI-Lab/research/<name>` 的冻结键。两个 graph 源仍逐项严格 SHA 比较，其他恢复/验证逻辑不变，旧 helper/checkpoint 完全保留。完整 diff 与源哈希见 `DERIVATION.json`、`path-adaptation.diff`。

启动参数明确提供以下原件，不搜索或自动 fallback：

- MC62：`restored-history/root/heroes3-ai-lab/evaluations/battle-observed-MC-probe-01/MC-update-62.pt`，原实验保存 SHA `5cd856b3221342c283899df126f4c50116d7779b3e0ea3b8d90125e243310354`。
- TRAIN batch：`verified-repair/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01/candidate-micro/phase-0/admitted-1.pt`，原 SHA `fd86a735a7e8597fd3329c999169dfb538cb484743b952bbced04f39751b0d16`。

工作流：

1. 严格检查完整 MC 分支边界：更新62、实际 Adam7936、环境计数31744、`mc_fragment_lambda1` 标记；恢复 CPU model、命名 Adam、计数及 RNG payload，验证完整摘要。
2. 用同一 MC62 在前八个已归档 TRAIN graph 上做 CPU 和真正 CUDA forward，覆盖 attacker/defender。logits/value 采用原 `<2e-4` 绝对门限、rtol0。没有新采样动作或 native rollout，不把 MC62 与旧61的 behavior logp 混比。
3. 实际恢复 CUDA model、命名 Adam、CPU/CUDA/Python/NumPy 四 RNG。分别真实 draw 13、13、5、5 个数，再恢复原边界重 draw，要求逐值相同，最后再次恢复原 RNG。
4. 从 live model、live named Adam、live counters 和已恢复全局 RNG 捕获保存载荷，其余全部 metadata 原样保留。完整 canonical payload digest 必须与原 checkpoint 相同；保存仅在新输出目录。
5. reload 新保存文件，完整 payload digest 与原件精确相同。再在新 CPU 对象和真正 CUDA 对象中恢复该 roundtrip，重核 model、命名 Adam、7936 计数和四 RNG 摘要。

所有 optimizer 实例的 `step` 被显式拒绝计数器替换，准入要求调用次数为0；没有 backward、游戏初始化、原生对局或 DEV/final-test 输入。新文件是零更新往返产物，不是新训练模型，不晋升。Torch 序列化文件 hash 可以因储存布局而不同；只有完整值/类型/键/张量形状与 dtype 的 canonical payload digest 精确相同才通过。

原资源门保持不变：开始可用内存>4GiB，随后>2GiB；swap<256MiB；GPU 温度<86°C、显存<14,000MiB。失败记录为工程停止，不重播种、放宽阈值或省略恢复步骤。当前只有标准库 AST/source derivation 检查，未执行 Torch/CUDA 资格。

root 启动前设置 `HEROES3_PROJECT_ROOT`、`HEROES3_LAB_ROOT`、`HEROES3_RESOURCE_ROOT`，后两者应与 controller 同一 lock 路径，传 `TERMINAL_CREDIT_LEASES` 及 `pass_fds`。`--out` 必须不存在，worker 会创建它；controller 的 stdout 日志可放在另一个父目录。worker 正常退出后 controller 应确认进程组无活进程，再释放 lease；锁文件不删除。
