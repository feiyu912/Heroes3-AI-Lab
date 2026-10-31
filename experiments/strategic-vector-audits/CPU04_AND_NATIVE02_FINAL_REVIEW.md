# CPU04 barrier恢复与真实GPU双环境采样独立复核

本次审核只读取已完成的原始证据，在CPU比较权重/optimizer/RNG与日志；没有启动GPU、游戏、backward或optimizer，也没有修改collector/trainer/v2/native冻结输入。复核器及逐项结果：`cpu04-native02-review-02/AUDIT.json`，附独立审计脚本副本。

## CPU04：确实重新生成独立fake环境，限定范围端到端精确恢复通过

核对 `trainer-cpu-continuous-04`、`trainer-cpu-split-04`、`trainer-cpu-resume-04` 三组实际输出和源快照：

- 连续2次update采16个fake episode，独立split采8个，加载split/update-1后又采8个；共32个不同run_dir、32个不同agent目录、16个独立wave batch token和16个不同临时lab root。
- 每个环境持久保存的worker.log包含本环境RUN_DIR和worker结果，native-pid.json的batch与本wave token一致；每个独立agent目录都有真实文件协议产生的4份request/action，未共享其他分支目录。
- 冻结trainer快照调用collect_parallel；collector快照为每个env新建Popen worker与空agent目录，没有从归档batch读取训练rows的替代路径。归档回放验证器是另一个测试，不混为本轮证据。
- 各wave显式synthetic=true、inference_schedule=barrier；采样checkpoint的全部tensor摘要与manager当次policy摘要对应。

独立重比两次update的每批32条存档：request、action、old_logprob、old_value、terminal return、generator_seed、policy_version、episode_id及policy tensor SHA全部相同；对应update-1与最终update-2的模型、Adam、CPU/Python RNG、已完成episode的generator state逐位相同，同协议SHA一致。连续进程实际8个Adam step，split进程4步，resume进程另4步，累计8；partial失败checkpoint记录实际1步且complete=false。

可以严格限定为：**本机、该CPU fake-engine协议、barrier推理与这两次update下，独立重新采样的完整边界保存/加载/续训逐位恢复通过。** 不能外推为真实游戏、CUDA或任意24环境都逐位一致。

证据限制：32个fake native `/tmp/throughput-synthetic-*` 目录在本次审计时均已不存在，因此没有声称重新读取已清除的fake client.log/原生轨迹；独立进程和新采样的判断来自保留的worker日志、native-pid/token、独立输入输出目录、完整rows和源快照。第一次复核尝试因要求这些临时目录仍在而停止，失败目录保留；第二次在明示限制后完成持久证据检查，没有改原数据。

## 历史02/03失败保留，不能由04替写

CPU02异步批次首次旧value舍入差进入tensorSHA种子哈希，后续随机流雪崩；CPU03已改逻辑update/job种子，环境RNG相同仍有动态batch浮点差，近零Adam参数的差异会放大。它们仍是failed报告。CPU04使用新的barrier协议，使active环境按确定性批次提交；04通过不意味着02/03原结果被修成成功，也不意味着归档批回放足以认证异步重新采样。

04源快照与当时冻结协议：trainer SHA `74dcbb58fecbc366a3a1834c9cb70bd500a82b0f1f45994d2a3913f887933df3`；collector SHA `88d657206c1603643f72deed36fdf50eb91db5a8bf628e2b69b6c0410e07122a`；算法 SHA `05477bfef29bb4b91c107b43a514c8284fa76e7817947f6f9e276354ed1bf088`；04 protocol SHA `92300ac26aaba79be857c27d0ca3ba7896eaeb1f39d8c1198755b44e4d46a17f`。该协议/来源不同于更早native-collect-02，不能混称同一恢复试验。

## native-collect-02：572个动作真实执行，GPU只采样没有学习

重读2局原生完整日志、strategy state、native决策、agent请求/动作、committed与accepted rows，按序逐条验证候选完整内容、所选index、player/day/hero/from、destination/next、文件SHA和policy身份。572条全部吻合：

| 我方角色 | 对手 | 决策 | 实际位移result1 | blocking visit result3 | move_applied ACK | 失败/拒绝/未确认末动作 |
|---|---|---:|---:|---:|---:|---:|
| 红 | EmptyAI | 156 | 152 | 4 | 156 | 0 |
| 蓝 | EmptyAI | 416 | 412 | 4 | 416 | 0 |
| 合计 | | 572 | 564 | 8 | 572 | 0 |

blocking visit是已执行的合法交互，不伪称位移。两局原始move reply数均等于请求数；无failed reply、move_failed、economy_failed、query_failed、服务器拒绝或external-policy-failed，最后动作没有使用“已终局所以默认执行”的豁免。client.log/state/decisions的内容SHA与原生result一致。两局对EmptyAI胜利只是课程/工程结果，未触独立测试，不构成对NK或MMAI/BattleAI的新胜率证据。

采样输入模型是旧学习权重迁移的 `threat-supply-initial-v3.pt`，SHA `804aab1aeb3fcc7e685891b469abe1efaf309399619f4d47771382f3d70571d0`；所有572条记录policy tensor SHA一致，collection-boundary和CPU重读该checkpoint的tensor摘要相同，manager采样前后digest门禁通过。collector该版本没有optimizer，报告actual_optimizer_steps=0；这是CUDA推理/真实CPU游戏采样，不能称GPU训练或新参数更新。

原batch记录remaining_processes=[]；本次再次按其专用batch token检查/proc，未找到遗留owned进程。原生source-snapshot与旧plan的SHA已保留；后续query-ACK gate编译是正常新版本，不要求当前native二进制永久等于旧SHA，也没有把旧采样冒称新门禁已经验证。

## 严格新PPO明确另起0更新prior

已只读核实新增 `strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt`：

- SHA `6ced669638242eff327c2b29c3ab635528f07167a7959a2170985f2dc304e2c9`。
- parent为未训练的v1 prior-initial-v2，SHA `8dd2cc8eeb09c2e83421fd0ec6c2958ba64716580e2dac74086bbb8d92f7e5d3`，parent_training_updates=0。
- trained=false、training_updates=0、optimizer_steps_total=0、optimizer=None；actor残差输出层权重/bias全0，新增信息列依旧显式迁移为0。

这是父窗口明确的研究决定：严格新PPO的数据准入与执行证明已经加强，不将历史弱门禁下更新过的参数默默算作新协议干净起点。旧804aab模型、pilot02、既有失败/成功轨迹和恢复证据全部保留；不是抹去旧训练，也不是声称旧全部样本必然无效。native-collect-02与CPU04仍以旧804aab模型开展，不能把其成绩算给新clean prior。

截至本审核，没有新严格GPU梯度训练、CUDA真实策略边界恢复、24环境稳定性或独立能力提升认证。下一规模扩展仍需按新冻结模型/原生门禁逐步实测。
