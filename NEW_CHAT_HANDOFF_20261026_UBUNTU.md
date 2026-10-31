# 2026-10-26 原生 Ubuntu 接续：四组补兵机制对照通过，完整goal仍active

先阅读并保留NEW_CHAT_HANDOFF_20261023.md、NEW_CHAT_HANDOFF_20261025_UBUNTU.md的完整目标/授权/保护。最新实际结果见experiments/strategic-refill-paired-build-20261026/REPORT.md，不能沿用本文件旧稿的“baseline仍在运行”。

baseline-build-01已确定exit1，720源编译完成但末client/server链接未找到ONNX间接依赖，原记录保留。新build_pair_link_v2.py仅加相同-rpath-link并修复Ninja跨子进程组的SID采样/清理；720compile_commands完全相同。baseline-build-02和candidate-build-01已通过并封存，root完整源/bin/配置/依赖/hostloader读回通过。所有已登记exec会话已返回，0当前编译/游戏/learner。

native-01四case×两臂8局真实完成，全部frozen独立pair审计及另一个raw独立review通过：44决策、14成功位移、6招募、2转兵，正常终局drain；正例允许继续探索1步后返城2步再合并，空库存/满7异种无exception，满7同种可合并。固定seed2026102601、blue1、EmptyAI、calendar诊断终局，不能计胜率或说学会补兵。0新PPO/Adam/晋升，final test未用。

新边界准备由当前子代理refill_prepare在strategic-refill-boundaries-20261026实施，只prepare、不native；原v1 freeze不改。具体自然证据：candidate正例q4选择Town后q5只有一个Town目标，库存仍正且未到城；q5到城转兵前state库存正，ACK后q6无Town零长度动作且恢复约47自由移动。此可说明自然去重/到达耗空后重选，不能拆成policy时库存仍正的独立零长度试验。需核新代理产物和剩余边界后再资格，不要跳PPO。

PROTECTION_AFTER_01已复核85旧SHA、60机制freeze、canonical锁相同inodes2752519/2752520，原生进程无活任务、GPU计算列表空。所有重CPU/native继续GPU→pool非阻塞真锁，继承FD，自己SID/会话全部排空后释放；单GPU学习器，训练16默认、24须实测。原accepted/source/bin/model与final test保护继续有效。完整研究目标仍active，工程与四机制通过不是最终完成。
