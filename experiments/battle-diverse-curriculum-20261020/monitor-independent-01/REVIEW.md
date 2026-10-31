# 进行中独立资源快照；不认证最终实验

主机器快照UTC 2026-10-20 14:05:09，读取窗口约0.13秒，之后只查已完成文件，未轮询/再采资源。launcher PID305持真实内核GPU与pool两锁，GPU learner PID400为其子进程且是nvidia-smi唯一compute app；没有发现其他训练命令。WSL将GPU进程名报为Not Found，但PID与实际训练命令匹配。

本快照正处于新phase的staged boot：实际11个direct worker，11个均映射libmlclient/libmlserverplugin/libvcmi/connector，任务中有runServer原生线程。原生嵌在worker内，不是另有11个独立native executable；不能将该资源点称16个完整native实例。此前本轮一次ps --forest输出观察到16个direct spawn worker（PID2408/2447/2483/2519/2558/2594/2652/2691/2727/2766/2802/2844/2880/2919/2955/2991），父PID400；那次没有PSS统计，因此不将两时刻拼成“16worker资源快照”。不为凑数暗中再测。

完整资源点：MemAvailable9171.8MiB、host swap0；本launcher子树PSS6446.9MiB、swap0。GPU物理占用2125/16303MiB、温度38℃、利用率1%；不能用模型alloc代替整卡占用。冻结driver已完成前8轮的16worker采样，稳定复制的训练报告记录最低可用内存6738.8MiB，但这是driver记录，与本独立11worker瞬时值分开。实际目标/已执行规模是16级，未做到24，也没有称24。

本次只认证当前已完整保存边界：update8、1024次累计真实Adam、4096个样本；检查点SHA、rollout SHA/字节数/元数据及488个冻结输入当前SHA一致。CPU仅读取序列化checkpoint，没有再做CUDA/全批概率回放。TRAINING_REPORT_SNAPSHOT.json是原training.json一次读取后的稳定副本，原字节SHA另在OS_SNAPSHOT.json中，避免把持续更新文件要求为静态。

AUDIT.json中snapshot_checks_passed仅表示所述检查通过，final_30_updates_and_64_DEV_certified明确false。30轮、最终模型和64DEV尚未完成，不能称实验passed或能力提升。native01的锁竞争失败仍保留为0native/0更新，没有改seed或追认。冻结运行输入未变，0新native/0GPU推理/0优化器；本次监测已结束。
