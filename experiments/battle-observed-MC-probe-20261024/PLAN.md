# 已观察终局片段：单次完整学习状态配对探针

依据仅来自既有TRAIN：原lambda.95终局延伸candidate链61个可延伸worker-phase片段、816条prefix行；MMAI其中508行有165行的终局TD系数低于1/4，最长距离51。原方法无独立胜局净收益。该统计不是唯一败因证明；lambda1可能增加方差。

固定原candidate-micro update61完整模型、命名Adam、CPU/CUDA/Python/NumPy RNG，实际7808调用。使用其真实原生、完全on-policy且已有完整审计的admitted-1 512行及1024行零损失suffix。没有新原生对局，没有重播种或重新挑样本，不把旧数据说成新数据。原16个worker的既有真实记录全部保留，不新增worker。

先逐步重放保存的行为：独立真实CUDA前向核对旧logits/values/logp，用原记录logits执行同形状Categorical抽样并核对全部动作，按原流程重算next-value；必须重建保存的学习RNG摘要且模型/Adam不变。使用保存logits重建的是历史抽样状态，不伪造新的原生调用。

先以原lambda.95目标复现update62；必须与原62的完整模型、Adam、四RNG、计数精确相等。若不等立即停止，保留证据，不进行MC分支。此复现有真实优化调用，只作验证，禁止冒充新的能力提升。

然后再次从同一个完整61状态恢复（不是空Adam初始化），重建相同的历史学习RNG。唯一目标因素：对最后仍在进行且suffix真实终局已被观察的253条片段行，用直到首次正常终局的真实已整形奖励总和作为Monte Carlo回报，adv=return-oldValue，相当于这些片段lambda1；早已结束的prefix片段目标逐项不变，suffix始终零loss。不变奖励、势函数、gamma1、优化器/LR、网络训练掩码、2epoch、batch8、entropy.005、KL.02与原始oldlogp。完整MC回报已与原生胜负减势函数以及独立GAE1验算。

每分支最多128实际Adam调用；复现必须与原128精确一致。MC沿原KL停止条件记录实际调用，不补步、不提高KL。若实际调用不等，报告处理包和预算差异，不声称等步数。输出独立完整MC62检查点；新arm标识使旧续训器拒绝静默按原方法恢复。完整学习器恢复与原生环境恢复区分：本项不恢复或启动原生环境。

GPU锁→pool锁，真实fd继承验证，单GPU进程，RAM启动>4GiB、后续>2GiB、swap<256MiB，GPU温度<86°C/占用<14GiB。CPU大分析和其他GPU工作须结束后才启动。不改任何历史冻结源、模型、运行证据或finaltest。

本项是方法探针，不自动晋升、不从训练目标变化推断强度。只有复现和MC完整保存/恢复证据通过后，才可在另登记的DEV比较同源历史62与MC62；DEV不作教师标签。本PLAN不授权打开finaltest。
