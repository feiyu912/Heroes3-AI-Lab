# 战斗PPO采样对手：本地源码与证书核验

身份修正（2026-10-24）：先前调查实际读取的是 `battle-terminal-credit-recovery-20261023-02`，不是当前 `battle-terminal-credit-recovery-01`。两者PLAN/FREEZE/RESULT和模型身份不同，不能以相同胜率视作同一次运行。原SOURCE_EVIDENCE、MiniMax TASK/REVIEW/session均保留为历史材料，不改写原始调用。当前01补充绑定见CURRENT_RUN_BINDING.json及下文。

结论：实际16 worker训练已混合原生BattleAI与公开作者原CPU ONNX MMAI；每phase各8槽，不是只对BattleAI采样。后续“加入作者MMAI”不是新因素。可以另设计50:50→全MMAI的对手分配处理包，但这不意味着会提升，更不能用本轮14→13推断缺少MMAI训练。

本报告由本地调查者只读源码/冻结/WORKERS/DEV证书得出；未启动native、GPU、编译、训练，未获取或改变资源锁，未读取finaltest样本。MiniMax只读最小摘录推理，见独立MINIMAX_REVIEW.md。

## 实际构造链

1. 注册：REGISTERED_CURRICULUM.json四phase×16槽，每phase4TRAIN case×2角色×2对手；64个case/role/opponent cell，每格64 admitted和64 suffix。原始freeze字节匹配。统计在SOURCE_EVIDENCE.json的registry，不按默认值猜对手。
2. learner配置：`/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/learner_impl.py:35-42`；SHA256 `060ec0961790bd8a755b8b994ed1315fbfa3f1f27b095134b39f83d766e58478`。按row的opponent显式传入；己方attacker选lab-upstream-defender.onnx，己方defender选lab-upstream-attacker.onnx。learner:91-93实际VectorEnv使用这些cfg，并保存WORKERS。
3. worker：`/mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-native-20261023/recorded_vector.py:18-20,27-31,46-51`；SHA256 `f6395c1b083255c2a8e367024403a6627bb3ebc0cc2cbfe3792cea879110637f`。关teacher，普通MMAI_MODEL直接传lab.make_env；仅MMAI_GPU分支改OTHER_ENV并启动GPU broker，而注册及实际WORKERS没有MMAI_GPU。
4. 工厂：`/mnt/g/Heroes3-AI-Lab/research/lab-env.py:5-12`；SHA256 `bdb325ee5cad7d5df952a35f7d357ef9f3bad4d624fe5bd2233b46a11f0b0dee`。明确把opponent/model交给v15 VcmiEnv；`/root/heroes3-ai-lab/src/gym/vcmi_gym/envs/v15/vcmi_env.py:339-378,430-437`；SHA256 `cd609f1ac8bb0224e63ba473dec1b8b3363771bad33e31e4cd9dee16ee205ae6`将对手置于己方反侧，并传redModel/blueModel，不把作者ONNX当己方学习策略。
5. worker资源：prepare-worker把每worker的Data/Maps/Mods链接到LAB共享只读数据树；`/mnt/g/Heroes3-AI-Lab/research/prepare-worker.py:5-18`；SHA256 `ca31495945969ea4a589ae6fa2479e894e7500d70255de36d551cee59f7aec9c`。这说明DATA/MMAI/models资源查找对应冻结的原始模型；不能覆盖共享ONNX来实现实验。
6. CPU与贪心：`/root/heroes3-ai-lab/src/gym/vcmi_gym/connectors/v15/threadconnector.h:170-179`；SHA256 `e078189037ac4cbd42f214058fe14955177100fb58fa962217e2879f853fd1dd`固定native temperature=0。`/root/heroes3-ai-lab/src/gym/vcmi/AI/MMAI/BAI/factory.cpp:39-53,86-93`；SHA256 `9c30c999464a2872f30371c65879367c173d314dcaa573919a3ae17ce022b6cc`普通ORT Session未附加CUDA EP，并构造CreateCpu memory；`/root/heroes3-ai-lab/src/gym/vcmi/AI/MMAI/BAI/v15/nn_model_v15.cpp:233-244`；SHA256 `bc139f922b6d678f95aa9b7491da60937b378cee9c94ec54413ce2bf68281345`temperature<1e-5选择最大概率首tie。controller:24-26拒绝LAB_NATIVE_ONNX_CUDA/LAB_ONNX_CUDA/TEACHER非零。限制：当前C++ factory/router/connector不是这份FREEZE逐源码记录的条目，因此此项是当前实现与冻结契约/WORKERS一致性检查，非历史二进制重建证明；未声称重审动态库构建。

## 原作者字节与实际运行证书

本地research/upstream-model-manifest.json记录公开作者smanolloff/vcmi-gym GitHub release v2.0来源，读取本地manifest，没有重新联网下载。原生共享数据文件当前SHA同时匹配原native01和历史 recovery-20261023-02 FREEZE：

- attacker：`/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models/lab-upstream-attacker.onnx`，19255061 bytes，SHA256 `62adf45ea34a323d72e9ce953a0c8b6740e60c3cec3651f282bfacee785d3151`。
- defender：`/root/heroes3-ai-lab/data/vcmi/Data/MMAI/models/lab-upstream-defender.onnx`，19255061 bytes，SHA256 `73bca79446ebdcab01e47fbbfada0162380df907bc86b19a21d0c502500cfaa9`。

历史 recovery-20261023-02/control-phase-3/phase-3/WORKERS.json与candidate对应证书均16 worker、8 BattleAI+8 MMAI_MODEL，两角色各4+4，worker Torch标志全False。对手模型路径已记录于实际configs，非仅PLAN陈述。

原始native01/FREEZE与历史 recovery-20261023-02/FREEZE及PLAN、WORKERS、DEV-RESULT、DEV-RAW-AUDIT的完整本地副本内容、原路径及各文件SHA位于SOURCE_EVIDENCE.json的certificates。DEV-RESULT明确parent60/control/candidate的MMAI为14/16→13/16/13/16，BattleAI均15/16；两个更新分支共同退化，不能把下降归因candidate特有terminal信用。此处只复读冻结评估证书，不声称再次重放96原始游戏。

## 后续方法边界（调查者判断，不是已执行计划）

若另做对手分配单因素：冻结同一个完整起点、Adam和各RNG；目标/奖励/PPO/rollout/phase/16槽与quota/role/map保持；只将预先指定BattleAI槽替换为原作者CPU MMAI，另保留50:50控制。修改slot对手标签意味着64-cell语义也改变，必须新目录新注册、新freeze和精确16槽清单，不可沿用旧“每case两种不同对手”断言或悄改旧冻结。重复同map/role的MMAI槽应明确计数而非伪称新增独立地图。共同seed不保证动作分叉后轨迹配对；固定rollout不等同固定完整episode或等墙钟。

改为16个CPU ONNX worker会提高ORT线程/内存压力（当前工厂intra-op4，原只有8个ONNX槽），需保留既有GPU→pool锁、单learner、staged boot和资源门；不能为速度改MMAI_GPU。先只读分层现有TRAIN失败：role/map/family/opponent、完整terminal vs截断、episode长度/phase-close未终止/目标和优势统计、动作概率/合法性、资源错误。因已有作者对手，盲目继续同配比PPO缺少新方法依据，但对手加权是否有效仍需新预注册对照，不能由本报告保证。

## 当前 recovery-01 独立身份绑定

已只读核验 `/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-01` 的PLAN/FREEZE/RESULT/DEV与两臂phase3 WORKERS。

- PLAN.json：当前01 SHA `6f43223eb904519b653d4b282b40119a17124a6e19e26eab636613765629bb0a`；历史02 SHA `fa8a8c2da58f07d2d400c94d9386389295737c9830d9b71e566abac0228af950`，字节不同。

- FREEZE.json：当前01 SHA `25e7a81bb35ff630854086f399854319c7f15ba1d5b78cc6dbf4b308b4033c03`；历史02 SHA `49ebc1799b18c1a7f3bdc1e1bdce01103e688c48ccd5c7de8518808fc93fd2d1`，字节不同。

- RESULT.json：当前01 SHA `a70bf041a8ce6c8a1dd765e35dbe4cdd90a95bf8654f8573425251a239b8779d`；历史02 SHA `e34aba74fe1cec702181e61c46e958c3c8fd5d47be8e035e3ca6f9c0b040eb16`，字节不同。

- 当前01 control checkpoint `/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-01/control-phase-3/update-68.pt` SHA `7fc48da22b317d597ef3156670d22b8cd5c901d324b5e039bf5e7aaad6f6d702`；Adam=8704。

- 当前01 candidate checkpoint `/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-01/candidate-phase-3/update-68.pt` SHA `e9f7c15cfcf05bbcb37690e40804e2da952094427d38ce60cf4f7753069fbf64`；Adam=8704。

当前01两臂实际phase3均16 worker、8 BattleAI+8 MMAI_MODEL（每角色各4），worker Torch均False；当前共享两作者ONNX hash匹配当前01冻结。当前01 DEV证书也为MMAI parent14/16、control13/16、candidate13/16，BattleAI均15/16；这个相同结果是单独读取当前01证书得到，不是把历史02结果迁移过来。故“已含作者CPU ONNX、candidate非独有退化”的结论也能独立绑定当前01。所有绝对路径、证书内容、SHA及源比对见CURRENT_RUN_BINDING.json。未重跑任何native/训练，未再调用MiniMax。
