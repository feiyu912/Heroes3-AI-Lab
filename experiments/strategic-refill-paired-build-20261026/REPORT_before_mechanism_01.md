# 原生 Ubuntu 补兵单因素隔离构建（2026-10-26，进行中）

完整战略/战斗 goal 保持 active。上一 goal turn 有实际迁移恢复及原生/GPU资格进展；本轮有实际工具链、依赖恢复、配置、独立审计和完整基线编译进展。尚未完成补兵运行资格或新能力评估。

重启后原项目盘未挂载，已用 udisks 挂载 code 分区；game 备份分区仅只读挂载。没有恢复 WSL、设置全局旧路径别名或安装系统开发包。当前实际硬件、内存及GPU快照见 CURRENT_RESOURCES.json，不沿用旧会话内存推断。训练并发尚未重新资格；本次仅 -j2 编译。

## 实际证据

- PROTECTION_BEFORE.json：历史85项 SHA 全一致，canonical锁仍为device66308、inode2752519/2752520；未另建锁namespace。
- ubuntu-native-toolchain-20261025/attempt-02：真实 C/C++20 编译、可执行链接及执行通过。第一次 GCC_EXEC_PREFIX 查找失败原样保留，移除错误变量后通过。
- 工具链补充来自73个精确原版包；官方InRelease签名、索引SHA、deb SHA及control校验，liblzma原版另从已验签20261001 Ubuntu历史快照获取。只复制所需缺文件，不安装系统。93普通新增文件及82链接；原4186输入完全未变。同包21旁支库保留且明确记录，不能称集合绝对最小。
- 最终 TARGET_DEPENDENCY_CLOSURE.json SHA d716b5712fd774c70924b6a44a8d0aff040b98bf7b145e9b232a8452811d84b3。138共享ELF在旧loader中真实解析，无stderr、宿主fallback或缺库。root独立读回4279普通文件SHA、168链接和138原始结果，见DEPENDENCY_CLOSURE_RECHECK.json；没有冒称第二次运行引擎。
- prepare-01独立复制完整source，无旧object/PCH或accepted修改。configure-01缺Boost配置的失败保留，补齐精确同版文件后configure-02通过；configure-03最终绑定不可变依赖闭包通过。
- GRAPH_AUDIT_CONFIGURE03.json：720编译项（707 TU及13 PCH），Director完整flags在构建路径重定位后逐串与原flags一致，所有ENABLE选项不变，显式include不引用宿主开发目录。用户目录scratch/安装路径为新epoch，两臂共用同物理路径。
- build-contract-v1.json固定九payload，仅CDirectorAI.cpp不同。内部BUILD_ADMISSION已在scratch保存，绑定最终配置、图和依赖证书，未要求用户重复确认。
- 基线实际完整编译已启动。LIVE_BUILD_STATUS.json保存最后观察进度、PID17964及exec session48885；此为活进程观察，不是构建通过。最终执行状态须看baseline-build-01/RESULT.json，观察超时不代表停止，不可盲重启。
- 补兵prepare实验：../strategic-refill-retention-qualification-20261025，四fixture、确定性选择器、collector、独立单局和配对auditor已落盘。原始交易守恒及故意破坏拒绝检查通过，源码冻结60项root独立SHA再核一致，见FIXTURE_FREEZE_RECHECK.json。尚无新native game，其他六边界未覆盖；准备检查不当作运行资格。

构建开始后工具链代理提出收缩同包旁支；经确认尚未发生任何prefix mutation，因此保持已经登记的完整工具链与证书不变，未prune。避免构建中变更输入。

## 继续执行

1. 先poll session48885或核PID17964/其进程组/RESULT；原进程仍活时只观察，不启动第二份build，不改prefix/builder/合同。两锁由实际controller持有并继承到子进程。
2. 基线通过后独立核capsule三binary SHA、完整source snapshot/manifest、实际命令、配置链、依赖闭包及保护后验；失败则保留原attempt并依确切错误调整，不删失败日志。
3. 在同scratch/工具链/flags构建candidate，仅一个cpp差异；封存独立capsule。完整构建并不等于新Ubuntu战略回归通过。
4. 按补兵冻结PLAN运行同fixture/seed双臂及独立raw audit。实际commit、远程recruit、可继续原目标、回城、全状态transfer+ACK和完整终局drain均须覆盖；不得静默换map/seed/放宽门。baseline正确缺少新增补兵项是对照预期，不得改写成候选资格。
5. 机制与新epoch运行资格后才登记固定TRAIN校准及有界PPO；历史rollout不得重标on-policy。沿用模型/命名Adam/四RNG与分支实际计数、单GPU、GPU→pool锁和final test封存。

本轮当前0新原生游戏、0 optimizer.step、0晋升。战斗历史对照的无净提升结论保持，未重复堆次数，也没有新的dsh/MiniMax调用。

## 后续实际结果：baseline-build-01 已终止失败

原session48885已经返回exit1，不再是活构建。所有720编译项完成，但最后client/server链接均失败：`libonnxruntime.so.1, needed by bin/libvcmi.so, not found`，随后`OrtGetApiBase@VERS_1.22.0`未解析。原冻结ONNX文件和SONAME链接实际存在，libvcmi动态RUNPATH也实际含profile ONNX目录；问题在隔离sysroot链接器的间接库搜索，不能说源码或模型训练失败。原RESULT/日志/资源和保护后验均保留。

已要求新build_pair_link_v2.py显式记录两臂相同的已冻结ONNX链接搜索适配，保留原driver不改。新配置必须证明全部compile_commands字节相同，才允许续用本次private baseline已生成的对象；不是复用旧WSL/accepted objects。需新配置、内部admission及新build输出，不能把旧exit1记成成功。旧完整compile阶段的失败/对象来源另绑定到新attestation。

另外，旧资源样本记录的是Ninja自身进程组RSS，峰值11544KiB；child ru_maxrss为1533812KiB，前者不能当作整个构建的并行总峰值。Ninja命令会建子进程组，新driver将按自己session SID覆盖所有子组进行度量和清理，锁持续保持到该session无活任务。旧样本原标签和证据不改写。

补兵工具只读独立复核见independent-tool-review-01；未发现确凿启动阻断/虚假通过问题。当前冻结60项再次SHA一致。实际原生地图覆盖仍未验证，0新native/0新Adam。
