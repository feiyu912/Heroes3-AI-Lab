# 并行训练入口与有历史动量的 forced 更新复核

本次只读审查 `strategic-vector-v1/parallel_trainer.py` / collector，并执行 CPU 合成动量探针。发现有效问题后先与owner确认没有训练或冻结边界测试运行，再修改新算法模块。未改冻结v2/native/模型文件，没有启动GPU或游戏。

## 已查并修的缺口

1. **旧parent文件被当作当前采样checkpoint。** 初稿每wave传入origin_path，即使实际manager模型已更新，plan中checkpoint SHA仍指初始权重。实际tensorSHA另有记录，因此不等于采样一定off-policy，但两者缺少对应证明。owner已改维护当前完整update-N文件，并在collector单次读取其字节，复算全部参数/缓冲tensorSHA与实际manager模型严格匹配，原始parent仅作lineage。
2. **父模型历史链与trained继承缺失。** v2迁移checkpoint自身training_updates=0而trained=true；初稿update0会误写trained=false，且没有内嵌完整parent_lineage。owner已补parent_lineage/parent_trained/reset_optimizer/reset_rng，旧训练史与新协议0步明确分开。
3. **冻结未覆盖原生配置。** owner已补原生bin/config递归文件和Mods JSON，避免建筑依赖/生物配置在采样中变化未检测。
4. **零actor直接梯度不等于不更新actor。** 原choice-ppo-v1已有Adam动量时，全forced批量actor目标0仍移动6个tensor，L2=0.01617936，state.step1→2。CPU证据 `strategic-vector-v1/forced-momentum-before-fix-01/AUDIT.json`。先与owner确认未运行后，新choice-ppo-v2在无自由选择minibatch的backward后将actor grad设None，Adam/AdamW因而跳过actor权重/动量/decay/step。after-fix-01真实CPU probe中非零历史动量max abs=0.00746678，actor权重与完整optimizerstate保持、step仍1，critic继续更新。

新算法当前SHA：`05477bfef29bb4b91c107b43a514c8284fa76e7817947f6f9e276354ed1bf088`；完整CPU不变量/invalid/实际步数测试03通过。全局Adam实际步数取参数state最大值，另单独报告actor/critic组步数；不再假设两组永远相等。

## 主干检查

- 实际执行CPU schedule函数核验：2/4/8 slots均采齐8个唯一job，2图×2对手×双角色每格1局；24 slots为3seed×8格、每格3局，无重复job。此检查没有初始化CUDA。
- 同一update先收齐全部wave，期间固定policy version和实际tensorSHA；所有有效完整终局之后才调用PPO。任一wave BatchAbort抛出后不会走本update的optimizer；已收前几wave只是暂存，不能用于partial更新。PPO再次验证完整manifest与episode唯一/长度/原生消费/合法±1。
- collector每env episode_id包含job、局部envindex、policy version及真实tensorSHA；跨wave的job/seed不同，trainer在整update检查8/24个唯一ID。
- CUDA设备创建前已获取唯一GPU learner锁，模型加载、CUDA种子/状态访问与训练均在锁内；模拟池由collector各wave取得，未并行启动多个learner。
- checkpoint单次字节读取产生SHA与模型/Adam/RNG；同协议完整边界才resume，目标updates是总数。原初始化recipe继承到resume协议，不被resume文件路径替换；算法实际epochs/minibatch值写入protocol，而非只引用默认常量。
- 部分失败保存complete=false证据并拒绝resume；异常后的optimizer真实步数取Adam state，CUDA_training只依本进程实际step，继承旧训练不计新更新。

审查时源码SHA：trainer `b3ae888a5996dcecd4cc47163649a3c70a9fdb94e4d7a818a2ec67fac8e9a889`，collector `bbb8d4b6247fe366f673c0fab954b78108744d276a3d16d7d115feb1db3f258c`。上述结论绑定该快照；后续新快照应重新检查，不要求研发树永久不变。

## CPU02端到端精确轨迹对照失败，未抹掉

`strategic-vector-v1/TRAINER_CPU_AUDIT_02.json` 明确passed=false。首次update连续/重新split权重已差6.50e-8；第二update模型max差0.00105558、Adam差0.00847540。CPU/Python RNG字节相同，不等于整条并行采样轨迹相同。

只读原始差异证据：`cpu-boundary-drift-02/AUDIT.json`（此目录），附审计脚本副本。

- update1的32条请求、动作、old_logprob、envseed全部相同，只10条old_value差≤5.96e-8；22条microbatch上下文不同。首差wave1/env0/request2：独立推理batch_size1与2，value分别0.6786514520645142与0.6786513924598694。
- 微小value变化进入PPO后，使update1输出tensorSHA不同。当前env_seed把policy version和实际tensorSHA一起哈希，故update2种子完全换流，32条seed全不同，继而6个动作、6个后续请求不同。
- 复算第1job种子分别178638500376628222与8315975314131055950，与原始记录完全一致。该差异不是“RNG没存”的直接证据，而是重新异步采样浮点差异与哈希种子放大的复合结果。

不能将这个failed报告改成passed，也不能仅放宽最终0.001参数差阈值伪称逐位恢复。后续若要求重新采样也严格轨迹复现，应另冻结确定性barrier/microbatch重放协议；或者把权重hash仅作审计身份、随机流采用稳定逻辑update/job种子以减少微小浮点变化的哈希雪崩，但后者仍不能保证所有采样动作逐位一致。当前collector在父窗口真实纯采样期间未热改。

## 隔离保存恢复的CPU证据

owner追加 `strategic-vector-v1/archived-boundary-cpu-01/AUDIT.json`：使用相同归档完整batch，首次update准确重现已保存权重/Adam/CPU RNG；实际保存文件、重新加载后执行相同下一批，模型、Adam、CPU/Python RNG逐位一致，总step8。已只读核对其脚本：加载模型/optimizer来自真实新读文件，连续/恢复模型互相独立，没有用同一个内存引用制造相等。

这证明该CPU归档批量上的序列化/optimizer/RNG恢复通过，**不能覆盖此前异步重新采样02失败**。collection_episode_RNG字段验证的是已完成局的generator state保存在文件后不变；归档重放未再次启动环境，也不认证中途环境恢复或下一次真实CUDA采样一致。

## 尚未通过的边界

真实GPU训练/完整native多wave恢复、24环境资源稳定性与独立能力提升均不由CPU合成/归档对照认证。首个GPU wave已有forward后若BatchAbort，旧report的CUDA_inference可能保守false（只在成功返回后置true）；此报告字段风险已发owner，未在运行中热改。CUDA_training真实step门禁与此不同，不能混为梯度更新误报。
