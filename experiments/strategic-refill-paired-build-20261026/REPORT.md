# 补兵单因素：首批四组原生机制对照通过

2026-10-26。完整战略与战斗 goal 仍 active，尚未完成。此处只有机制资格，没有学会补兵、整局能力或胜率提升结论。

同一源 epoch、同一个物理隔离构建目录、同工具链/编译优化/功能开关、相同运行资源，每个case两臂地图字节和种子完全一致。九份payload中仅DirectorAI.cpp不同：保留原探索commit，同时允许已经由原生寻路生成、且可接收兵力的己方城镇补兵候选。没有改奖励、PPO、初始化、协议或自动强制回城。

| 注册条件 | 原schema6基线 | 补兵保留候选 | 独立配对审计 |
|---|---|---|---|
| 正例：离城后远程招募入镇库存 | 只保留原探索移动，无返城选项 | 原探索可继续一步，再返城两步，实际转兵1次 | 通过 |
| 空城库存 | 不增加补兵项 | 不增加补兵项 | 通过 |
| 英雄七槽满，库存物种不匹配 | 无补兵项 | 无补兵项 | 通过 |
| 英雄七槽满，库存与已有槽同种 | 无补兵项 | 允许返城，what=2真实合并，七槽仍为七槽 | 通过 |

共8局原生游戏，44次策略决策、14次成功实际位移、6次招募、2次实际转兵；44个typed动作ACK另加2个转兵ACK。两个正例候选各4次位移：离城1次、继续原探索1次、返城2次，不能说成4次返城。完整招募/库存/军队/资源守恒、服务端应用、实际ACK、原生坐标、实际加载二进制及libvcmi路径/inode/SHA、runServer线程、正常exit0和终局原子drain均通过。

首前缀相同，处理发生处只多一个合法Town kind4；负例前缀也完全一致。独立第二审查另从原始请求/动作/typed/log重构计数、军队delta、移动坐标和唯一CPP差异，不只读取passed。见independent-raw-review-01/REPORT.md及AUDIT.json（SHA463c5cf6bfc0637ce3176276d227ebeb750cb2de1fd37db0113edfbd8e39346b）。单局/配对审计均未额外运行游戏。

所有8局均为固定seed2026102601、控制blue/player1、EmptyAI对手、daysPassed=3诊断终局。它们不是多地图/多种子/双角色/双对手能力评估，calendar终局不算胜局。0新训练样本、0optimizer.step、0模型晋升，final test未使用。其余边界资格与新epoch战略能力资格仍未完成，尚未启动新PPO。

## 构建及保护证据

- baseline-build-01完整编译后末两exe链接失败，原日志/exit1保留。原版ONNX库实际存在；新v2 driver只为两个exe显式加冻结ONNX目录的-rpath-link。
- configure04的720条compile_commands字节与configure03完全一致；720个本次private对象/PCH重配置前后SHA全同。旧WSL/accepted对象从未复制。首次失败的实际编译来源另字段绑定到最终attestation，不伪造其exit0。
- baseline-build-02、candidate-build-01真实完成并分别封存。client两臂SHA相同692fc134fd13445c858e328556aaef4d6e2088f2aa548335554e71f94901c235，server相同9ebd385189a06c336cfd43dbe2139a32c215a9f3630cf45a523861ef11a51dc3。
- libvcmi：baseline880df6ab699216feb54f7d61c34a3f465473f2a5bbfd430747d64a5e93193ad5；candidate25de2bded42150eb2703355c63ab44959c736c809835c9425cbbb19f9df1bb32。
- baseline-independent-01与candidate-independent-01：完整3701条source manifest、实际编译命令、配置链、4279依赖文件/168链接读回、三个二进制实际host-loader依赖解析通过。138旧目标ELF的工具链闭包证据也保留；两种检查作用域不同。
- 原始driver只采Ninja进程组，旧11MiB数值不能当总构建峰值。v2按自有SID采样/清理，实际记录多个子进程组；candidate独立/proc观察也证明所有观察到的编译进程继承同两把FD/inode。采样仍可能漏短峰，实际child ru_maxrss不等于同时总RSS。
- PROTECTION_AFTER_01：85项历史保护SHA逐项一致，原生进程已无活任务，GPU计算列表为空；同canonical GPU锁→pool锁再次真实取得/冲突探针并释放。原锁文件未替换，accepted/profile/frozen模型未修改。补兵60项冻结输入再次SHA一致。

详细计数见MECHANISM_RESULTS_01.json；原始数据在native-01，四组原配对审计在各case-pair-independent-01。第一阶段构建记录另存REPORT_before_mechanism_01.md，失败不覆盖。

## 下一步

先在新的strategic-refill-boundaries-20261026目录补齐边界证据，原v1 freeze不改。自然轨迹可能已包含Town commit去重、到达及耗空后自由重选，但须独立审核其实际覆盖；不能把当前位置与auto-transfer耗空的混合条件说成两个独立因素。仍需不可达/非己方/目标失效/legacy等合法运行条件。全部资格完成后才登记固定TRAIN校准，再决定是否进行有限新鲜on-policy PPO；旧rollout不重标、不抄DEV教师。战斗的既有无净收益对照结论保持，不追加原已完成预算。
