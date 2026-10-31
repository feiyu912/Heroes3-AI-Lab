# 真实CUDA边界对照与新server屏障存档恢复准备

本次只新增独立审计/准备脚本，没有修改冻结parallel_trainer、collector、v2模型/encoder/broker或native；没有获取pool锁或启动游戏/GPU。

## 并行PPO CUDA完整边界

已有 `audit_async_boundary_cpu.py` 针对固定CPU夹具，硬编码synthetic、8step和特定目录；不宜直接把其passed标签当成真实CUDA认证。它还没有将first_update_model纳入passed条件，未校验完整manifest、source快照、当前权重checkpoint、实际CUDA数据和非空CUDA RNG。更早v1 `verify_training_boundary.py` 调用旧trainer，不能用于新parallel协议。

新增 `compare_parallel_boundaries.py` 仅分析三个已完成目录，默认device=cuda、synthetic=false，严格检查：

- continuous完成updates1/2，split独立完成update1，resume从split/update1完成update2；每进程真实Adam step与metrics一致，CUDA_training/实际device对应。
- 原始初始化parent、resume parent文件SHA/reset标记、协议内容和规范JSON hash一致；每个代码源都匹配保留的source-snapshot。初始化边界、两次更新边界都比较。
- 每update收齐2图×2对手×双角色8格；24模式每格3局，否则每格1局；episode_id唯一，同update所有wave同policy摘要，采样checkpoint确为该update前一个完整模型。
- 每局实际request/action文件与commit和native candidates/index/destination/next相符；真实CUDA运行还检查native原始日志/trace SHA、执行审计与无拒绝/失败，未确认末动作不能悄悄接受。
- 对应每局request/action/old_logprob/old_value/return/seed/version/episode_id全部逐位比较；模型、Adam、CPU/CUDA/Python RNG、每episode generator state、update数、dim/encoder/source协议全部比较，CUDA RNG必须非空。

任何差异保留首批具体位置/max delta，返回失败，不用容差放宽偷换“精确通过”。不同lineage造成的checkpoint序列化文件字节不要求相等。

已运行的工具自身CPU验证：

- `generic-comparator-cpu04-03/AUDIT.json`：显式 `--device cpu --synthetic` 对真实重新生成fake环境的CPU04三目录全部通过。
- `generic-comparator-reject-cpu-as-cuda-01/AUDIT.json`：默认CUDA模式拒绝CPU夹具，不伪造CUDA认证。

真实实验应在新原生门禁验收后、新唯一root中严格串行执行三个learner，所有输入保持同一冻结；例如4env下，前两组显式用clean prior初始化，第三组resume split/update1。三个命令必须保持environments、epochs/minibatch、seed-base、wall budget、inference_schedule等参数一致；target updates是总数。不得重复使用已有输出。

完成后三目录审计：

```text
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-audits/compare_parallel_boundaries.py --continuous <root>/continuous-2 --split <root>/split-1 --resume <root>/resume-2 --out <新审计目录>
```

本工具不启动上述实验；当前仅CPU工具验证通过，真实CUDA完整边界尚未认证。

## 新native fresh new-policy smoke的存档恢复适用范围

`verify_native_restore_v3.py` 仍可比较：同模型new-policy、同native/source/map的fresh原局，与其first-own-turn存档加载后的全局trace/decisions/targets、request/action字节和winner。它不是PPO optimizer/RNG恢复工具。

但该旧入口会任取save_files第一项、强制new-policy，且不会预先核对原局checkpoint身份、原局模式和新server屏障。直接把旧v6/v7的agent目录或不同模型传进去，失败不能归咎于新恢复机制；不应在新版本验收时混用。

新增 `prepare_native_turnstart_restore.py` **只做预检查并生成命令，不启动恢复游戏**。它要求：

1. 新原生fresh map原局完整通过，mode为new-policy/policy新模型，不是legacy/supply-aware，也不是另一次restore。
2. 请求的checkpoint SHA与原smoke-plan和broker-ready完全一致；所有v3请求/动作和native选择逐条对齐。
3. 原局/source/runtime与当前保持同一冻结快照，save原字节SHA匹配，唯一director-v5-initial存档必须正好是旧restore入口会选的第一项。
4. 新 `adv-server-battle-barrier-v1/installed-source-sha256.json` 三个server源SHA匹配；原局日志必须真的出现 `Adventure battle barrier ready for player`，防止只换最新源码却仍用旧v6/v7二进制/原局。
5. 原局没有move/economy/query失败和服务器拒绝，首trace为first-own-turn起点。

运行方式（在acceptance05通过后取得新的fresh new-policy agent目录再调用）：

```text
/root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-vector-audits/prepare_native_turnstart_restore.py --original-agent <新的agent目录> --checkpoint /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v2/checkpoints/threat-supply-clean-prior-v3.pt --out <新的准备目录>
```

准备通过后PREPARATION.json中的restore_command指向尚未创建的子目录restore-run。该命令随后真正启动原生恢复游戏，必须待共享pool可用并维持同一冻结直到结束；准备通过本身不算恢复通过。原工具的300秒外层等待包含pool排队，若排队导致超时应记工程中断，而不是模型负局。

已用旧 `v3-visible-info-smoke-01` 实测预检查拒绝，错误明确为没有新server barrier实际marker，game_started=false；证据 `restore-preparation-reject-old-v3-01/PREPARATION.json`。这是预期门禁，不是假装旧恢复测试损坏。

`restore-preparation-cpu-01/AUDIT.json` 另用标明SYNTHETIC_ONLY的CPU夹具检验准备器正路径、拒绝legacy模式/错模型/缺新barrier marker/不唯一save/native失败共5类反例，全部通过；没有用合成夹具冒充恢复成功。

新server `pendingBattleBarriers` 是瞬态且未序列化，因此当前只允许**没有active battle的first-own-turn存档**；不承诺任意动作、查询栈或战斗中途恢复。后续新native验收、fresh smoke及真实加载对照都必须分别留证。已完成的旧恢复证据保持原版本范围，不能自动迁移成新server屏障认证。

新屏障可能产生终局后的纯ready通知。准备器不按“terminal之后有任何记录”机械拒绝，也不删除原始尾记录。旧restore工具仍保留完整trace字节比较；若字节差异仅涉及时序通知，必须另出独立语义审计，限定为acceptance06已经验证的通知白名单，且除event标识外每个状态字段与terminal完全相同、没有新增request/action或状态改变，才能报告该差异性质。严格字节不等依然原样记录，不自动改成passed，也不能把真实未执行动作包装成通知。
