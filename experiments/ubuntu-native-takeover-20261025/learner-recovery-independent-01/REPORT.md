# 零更新 learner 恢复：独立 CPU 审核通过

本次在已通过41包 RECORD 检查的新 Python 环境中实际加载原 MC62（SHA `5cd856b3221342c283899df126f4c50116d7779b3e0ea3b8d90125e243310354`）和本轮保存文件（SHA `939eb65da3d335a1b928ae6ddb193e68ab73df66bb4f8c6817920d096e84bdb3`）。没有只接受 producer 的 passed 标志：逐键、类型、张量形状/dtype/值直接比较，并独立调用原冻结 digest 重算，完整 payload 均为 `984fe79e7a31ae8aeb2ecedecaa27cc03a466b18d49274918e3a261e1427fc4a`。

模型、194个命名 Adam slot 的 moment/step、全部 metadata、四类 RNG 保存载荷和计数精确相同；仍是完成更新62、累计实际 Adam7936、环境计数31744，没有新更新。命名绑定从冻结 FullGraphPair 的 last 模式参数次序和原批准检查点推导，未创建 optimizer 对象。Torch CPU、Python、NumPy 三个私有 RNG 还实际重复抽取13/5/5个数验证载荷等价；CUDA RNG 在本独立审核中仅检查全部原字节，不触发 GPU。

原 SHA 绑定 TRAIN batch 的前八个完整图（attacker/defender各4）已在 CPU 重新 forward，logits 与本次 `NN_COMPARISON.pt` 保存的 CPU 结果精确相同，value 亦通过原误差门。存档 CPU/CUDA logits 最大差 `7.2479248046875e-5`，value 最大差 `3.5762786865234375e-7`，通过原 `atol=2e-4, rtol=0` 门。每个 TRAIN 图的完整摘要、合法动作数及角色已单列进 AUDIT；没有用旧61 behavior logp 冒充新 MC62 的输出。

v2 source freeze 的10个文件、controller 源 SHA、实际命令/输入、worker RESULT SHA、Python profile 证书、正常退出/进程组排空及两把锁的 metadata 相互一致；当前锁文件 device/inode 仍与该次运行记录相同。本审核没有重新取得锁，也无法重新检查已退出 worker 的旧 FD。历史真实继承/exclusive flock 证明依赖本次已冻结并实际完成的 controller/worker 代码及绑定记录。

资源记录只有开始/结束两个端点：可用内存25,490.11→23,921.26MiB，swap均1.1875MiB，温度45→46°C，GPU已用显存932→1422MiB，均满足原门。它们是端点采样，不是整个运行的连续峰值记录。

实际 CUDA 执行的证据来自已冻结 v2 源码中的 CUDA 对象放置、真实 forward/synchronize、CUDA RNG draw 和 reload 恢复，以及本次正常完成的 worker/controller/telemetry、保存输出的一致性。**本独立审核未初始化 CUDA，没有第二次 GPU 重跑**。审核自身仅 CPU，0 optimizer对象、0 optimizer.step、0 native对局、0 DEV/final-test 输入；模型及全局 CPU/Python/NumPy RNG 未改变。

证书见 `AUDIT.json`，逐参数 Adam 绑定见 `NAMED_ADAM_BINDING.json`，可复跑入口为 `audit.py`。另引用 `../battle-independent-01/AUDIT.json` 已独立复核的4个历史重复完整对局、102个决策；本次没有重复其游戏或NN审计，也没有把技术回归计作新独立胜率。此结论仅说明新 Ubuntu 环境中的 learner 完整保存/恢复边界成立，不恢复在途原生游戏、不证明模型能力提升。
