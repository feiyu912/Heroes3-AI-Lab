# 暂停交接：2026-10-19

用户明确要求“可以停了，之后再干”。goal已paused；必须等用户恢复，不继续训练、构建或实验。原始入口NEW_CHAT_HANDOFF_20261018.md与CURRENT_PROGRESS_20261018_TAKEOVER.md保留。

## 停止时实际状态

- root实查：无vcmiclient/vcmiserver、训练、ninja、capsule构建或boundary runner进程；nvidia-smi无compute进程，GPU学习锁与共享模拟池锁均可独占。首次进程过滤因WSL无rg未完成，随后用Python读ps确认，不能把第一次失败当检查通过。
- 两个正在工作的子智能体均已回报停止，无各自活动进程或锁，并保存STOP_STATUS.md。实现agent明确：candidate/manifest落后于最近未测模板编辑，不得直接build；31项standalone codec/SHA synthetic检查和早先两个真实TU syntax-only通过，不覆盖后续编辑。新bundle helper尚未运行/语法测，copied v3报告不是v4证据。完整结构化boundary观察仍未完成。独立review的兼容gate及const读取修复尚未重新复核。
- 没有新v4原生构建或游戏。旧冻结源码、capsule、模型和历史证据不修改。

## 现在到底达到什么

1. 原先第三轮超时已作原生回放诊断并修复相关行动/回合/战斗边界；实际GPU更新、完整checkpoint恢复与独立配对评估均已有证据。schema4研究模型539850b6…完成164真实CUDA Adam步，小规模DEV为旧模型5/8→新模型6/8，不能称广泛能力提升。更早accepted模型仍9a6b15c6…，没有替换冻结环境。
2. 连续训练与中断恢复得到真实原生采样验证：模型、Adam、RNG与1544请求/动作文件精确对齐。24并发纯采样已测过，不代表24并发新模型训练。
3. 双英雄有限库存运输实际通过独立复核：城镇10枪兵由信使取走并送给主力，主力5→15，信使原3弓箭手保全；98完整脚本事务、跨6个自身回合。这是部分机制验证，不是完整对局胜利，也不是持续招募或神经多英雄策略。权威报告experiments/strategic-multihero-supply-native-v1/CARGO_V3_INDEPENDENT_REVIEW.md。
4. 坐标回撤脚本固定DEV八对4/8→5/8，净一局；不是神经学习/人类战术成果。严格终局请求确认修复已实机复核，原三个失败批次保留且未评分。
5. 新战术脚本16局配对反而4/8→3/8、永久损失多4，已否决；0认证人类专家课程、0可直接训练的专家标签。不能粉饰成战术提升。

仍缺完整战略AI：神经策略仍单英雄；经济脚本；战斗仍原生BattleAI。尚未证明对MMAI稳定取胜或对BattleAI达到95%，未做最终独立holdout。

## 暂停中的实现与下一入口（用户恢复后）

- 新experiments/strategic-multihero-supply-v4正在实现非空任务中途原生保存/加载：完整控制文本写入playerLocalSettings真实序列化，SaveLocalState→SaveGame实际ACK，加真实成功marker/file/header/SHA，fresh加载原生嵌入文本恢复。尚未finalfreeze/build/native认证；已有CPU文件/报告不能混为原生通过。
- 独立复核目录experiments/strategic-supply-checkpoint-audit-v1；请先读双方STOP_STATUS.md。已发现旧schema4 typed load可能被新supply gate误拦，需要确认修复。decoder负count/无效坐标也需确认。不要靠旧草稿manifest/CPU报告推断最终状态。
- root新runner experiments/strategic-supply-boundary-native-v4/run_native_boundary_v4.py仅syntax/help过，未运行。仍待将manifest门禁收紧为13文件/明确epoch，checkpoint-turn只允许2；fresh复制bundle时save_file应重指实际副本，并冻结原/新bundle，去除reference旧路径依赖。
- 恢复试验计划：turn2真实cargo10在途且已有动作ACK的干净非零预算边界主动save，reference继续；父进程验证实际存档并原子bundle；fresh进程hydrate，再比较完整任务/预算/visited/目标和每个完整原生事务，截止首次ownturn6观察。保留轮询超跑尾部，不用全文件zip假装一致。随后补旧schema4 save/load兼容回归。
- 主代码WSL /root/heroes3-ai-lab/src/vcmi-adv；G盘vcmi不是同一棵源。原环境保持：Director cpp e198e32f9d3c787e14d575f2fe1c33bba44a8d1351403ffc833c54e4a3079b00，client b94162bb0d20566ae88512457bdb33266415d338fe92e50c4a6aa6dbd578dd78，server bbe0de38b7791c7900b2393d1809b38f5f1856ac8922f30d742095759cd43fac，lib d7016313e9f0e0dfc36d46a9e24d718fb2e7552e6433b5dcd0ca6a26cdaa285a（此前idle-after-cargo-01实测，本次未重新全算SHA）。

重新开始前核进程/双锁/冻结SHA；只一个GPU学习器，GPU锁后pool锁；已运行输入保持冻结，修改用新epoch/新目录，失败保留且不评分。用户本次暂停后不得自动推进。
