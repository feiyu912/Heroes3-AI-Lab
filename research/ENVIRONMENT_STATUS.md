# 战斗环境：已运行成功

**最新goal更新（2026-10-14）：** GPU正式训练与10组PPO等预算实验已完成，随机对手seed修复及独立重播通过。当前模型对BattleAI测试55%，但随机对手8/80到回合预算；不能称全面稳定。当前版本是runtime-manifest-v3.json，主进度见 [GOAL_PROGRESS_AND_RESULTS.md](../GOAL_PROGRESS_AND_RESULTS.md)。

**2026-10-14更新：** 教师标签映射已修复，12环境采集480场真实BattleAI决策，BC与Masked PPO均已实际运行。最新训练结果见 [TRAINING_THROUGHPUT.md](../TRAINING_THROUGHPUT.md)、[DECISION_MODEL_BASELINE.md](../DECISION_MODEL_BASELINE.md)，当前原生接口版本见runtime-manifest-v2.json。下文“尚未训练”等描述仅对应2026-10-13的历史验证。

验证日期：2026-10-13，北京时间。**VCMI训练引擎与vcmi-gym v15已在本机WSL2跑通真实战斗。** 完成状态读取、合法动作执行、终局返回、连续重置和独立进程固定种子重播。模型训练尚未启动。

后续验证已补充服务器伤亡/战前兵力接口，并完成1/2/4/8环境并行测试。详见 [战损与并行实测](BENCHMARK_RESULTS.md)，以下首轮运行记录保留历史范围。

## 验证结果

| 验证 | 实测结果 |
|---|---|
| 引擎构建 | libvcmi、libmlclient、训练server plugin、vcmiclient、vcmiserver构建通过 |
| Python连接器 | v13/v15 connector与exporter构建通过；实际战斗验证使用v15 |
| 实际战斗 | 3个独立进程，共15场，55次由Python选择的合法决策 |
| 连续reset | 每个进程5场均到真实terminal，没有truncation |
| 正常结束 | 三个worker均exit code=0；原先headless关闭崩溃已修复 |
| 固定种子重播 | 两个独立attacker进程的5场episode逐场数据完全一致，包括动作、reward、观测轨迹hash与终局字段 |
| 两侧控制 | attacker与defender均成功；测试不是同时训练双方 |
| 原有源码/游戏 | G:\Heroes3-AI-Lab\vcmi工作区仍干净；Heroes3.exe SHA256与调查时一致；没有向F:\heroes3写入 |

测试场景是从Gym ml-mini派生的独立地图：红方20名弓箭手、蓝方10名弓箭手，清除英雄技能/魔法预设并设0法力，无随机军队/障碍/攻城。使用确定性的合法攻击优先策略对BattleAI。这是运行/协议检查，**不证明自研AI的竞争力**，也不是公平兵力胜率比较。红方赢是预期的场景结果。

详细结果：[验证汇总](smoke-verification.json)、[攻击方第一次](smoke-attacker-1.json)、[攻击方重播](smoke-attacker-2.json)、[防守方](smoke-defender-1.json)。同目录保存对应worker日志；最后一场引擎日志位于WSL训练副本data目录。

一次运行5场的脚本计时约0.9秒（含约0.7–0.8秒环境启动，不含完整进程关闭）。这是极小固定场景的观察值，**不能换算为一般战斗训练吞吐、并行容量或模型训练时间**。没有做全面RAM峰值/CPU调度/GPU训练测量。

## 直接复跑

Windows PowerShell，在项目目录运行：

```powershell
.\RUN_BATTLE_SMOKE.ps1
.\RUN_BATTLE_SMOKE.ps1 -Role defender -Episodes 5
```

输出写入 `G:\Heroes3-AI-Lab\research\smoke-manual.json`。运行3进程/15场的完整回归与重播比较：

```powershell
python research\verify-battle-smoke.py
```

脚本会检查真实终局和worker退出码，失败即报错。运行目录、种子、依赖与动作选择均固定。模型没有参与本次测试。

## 文件与版本

- 独立WSL工作目录：`/root/heroes3-ai-lab`；目前整体约4.1GiB，包含源码、构建产物、独立资源、工具和日志。
- Gym源码：`/root/heroes3-ai-lab/src/gym`，基于 `11241d496db95541766498373e23245a67847a97` 的源码快照。
- 训练引擎：同目录 `vcmi`，基于 `e956242503f465ae6ec0a62a3aeb2c4ea179db5c`，加下述本地补丁。采用固定提交压缩包解压，没有假装这是新的官方release或完整git checkout。
- CMake 3.31.10、GCC 11.4、Boost 1.74、SDL2、LuaJIT、SQLite3；ONNX Runtime CPU C++库1.22.0；pybind11固定gitlink v2.13.6。
- 独立Python环境：`/root/heroes3-ai-lab/venv`，Python3.10、Gymnasium1.2.1、NumPy2.2.6；没有安装大型Torch/GPU训练依赖到WSL。
- 游戏资源复制在`/root/heroes3-ai-lab/data/vcmi`，训练副本`vcmi/data`通过链接访问。仅复制所需LOD/SND与VCMI/ML资源，没有导入HotA。

训练分支原先在ML构建中把用户数据目录硬编码为相对`./data`，首轮按实际路径挂载独立资源。后续已补充XDG_DATA_HOME支持，用于隔离多进程数据目录。此外本分支的“开发目录检测”需要客户端/服务器可执行文件存在，只构建libmlclient会漏掉源码配置目录；现已一并构建两者。

## 修复及证据

[保存的补丁](wsl-build-fixes.patch)只修改WSL训练副本：

1. VIPBot的候选hex形参使用已有BattleHexArray引用，避免Boost1.74容器不能转换成std::span的编译错误；不改变候选遍历逻辑。
2. ML库明确链接Boost stacktrace，修复Python动态加载时未解析符号。
3. shutdown增加已有flag保护，防止connector与引擎尾声重复销毁。
4. headless退出时不访问GUI专用AsyncRunner。GDB定位崩溃发生在shutdown中的TBB等待；GameEngine(headless)没有初始化该对象，故无GUI模式跳过此等待。

保留了[退出故障诊断](shutdown-diagnostic.log)和[构建日志](wsl-build.log)。没有通过强制杀死成功进程、忽略崩溃退出码或绕过env.close来声称成功；env.close触发训练分支既有的整进程退出流程，所有测试worker实际以0退出。

构建/资源/修复脚本在research目录：wsl-configure.sh、wsl-build.sh、wsl-prepare-data.sh、wsl-compat-fixes.py。现有环境可增量复建。依赖包安装在WSL Ubuntu中；源码与小型安装包下载缓存在research/downloads，总体没有下载训练数据集或大型模型。

## 仍需验证的边界

- **原始v15相对军队价值不能直接当作永久伤亡。** 后续准确定位为防守方首个可决策状态可能已承受先手损失，而非此前推测的终局残余值。已增加战前数量/服务器BattleResult伤亡并验证普通无魔法战斗；复杂复活/召唤和完整地图持久结算仍需专项验证。
- 原地图带有format revision与artifact选择警告，当前简化场景能运行；正式基准需固定兼容格式并核对生成器/英雄初始条件，不能将警告当无关信息丢掉。
- 引擎有battleGetFightingHero访问检查的FIXME警告。正式公平比赛需要观测权限审计；本次不宣布迷雾/对手隐藏信息公平性已通过。
- 相同构造seed能复现整个episode序列；同一进程每次reset继续消耗RNG，连续场次轨迹可以不同。`reset(seed=...)`没有被验证为引擎级重播。
- 一个worker只启动一次VCMI实例；关闭会结束整个worker。多环境采用独立进程，后续已完成独立目录与1/2/4/8worker小场景吞吐测试；正式复杂战斗容量尚未测量。
- 无主动魔法策略训练、攻城全覆盖、完整大地图RL或模型优于BattleAI的证据。

下一步优先：服务器权威永久战损与终局原因 → 每worker目录隔离 → 2/4/8环境轻量吞吐/内存 → BattleAI轨迹采集 → 最小候选评分模型。当前里程碑是可运行战斗环境。
