# 接收核查清单（human-tactics-events-v2 窗口）

接收时间：2026-10-18 00:30 (Asia/Shanghai)。新窗口战术任务书：
`NEW_WINDOW_HUMAN_TACTICS_TASK.md`；并行边界：`PARALLEL_WINDOW_COORDINATION.md`。

## 接手时只读核查（未改动任何活动文件）

1. 进程：WSL 无活动训练/评估 python 进程（仅 networkd-dispatcher、
   unattended-upgrades 系统进程）；`.pool-lock` 为 0 字节旧文件（未持有）。
   → 未杀任何进程，未凭旧 control.json 断定状态。
2. 文件：读取 WORKBUDDY_HANDOFF.md、WORKBUDDY_REVIEW_20261017.md、
   WORKBUDDY_NEXT_TASK_STRATEGY.md、human-tactics-v1/INTERFACE_AUDIT.md、
   EXPERT_PILOT_RESULTS.md、BRANCH_INTEGRATION_REVIEW.md、
   TACTIC_CURRICULUM_DESIGN.md、EXPERT_OPPONENTS.md、TACTIC_BENCHMARK.md 等。
3. 引擎仓库识别：`G:/Heroes3-AI-Lab/vcmi` 是上游 vanilla VCMI git 仓库
   （无 MMAI）；实际运行引擎在 WSL `/root/heroes3-ai-lab/src/gym/vcmi`（非 git）。
   → 未把 Lab 根目录当引擎 git 根；未在上游仓库建 worktree。
4. 实验目录：`experiments/human-tactics-events-v2/` 原不存在 → 新建，
   旧 `human-tactics-v1`、`recovery-v2`、`expert-knowledge-v1`、`research/` 只读复用。
5. 资源纪律：所有本窗口游戏模拟经共享锁；未启动 24worker；未并行第二个 GPU 学习器
   （BC 训练前检查 /proc 学习器进程）。

## 隔离运行时构建记录

- 副本：`/root/heroes3-ai-lab-events-v2/src/gym/{vcmi,vcmi_gym,maps}`（cp -a），
  config/data/cache/models 独立；onnxruntime 符号链接共享（只读）。
- 构建路径重定向：`remap_build.sh`（sed 重定向 + 删 .ninja_deps + touch 消费者），
  仅作用于副本 build 目录；原构建目录未动。
- 原生补丁：`apply_native_patch.py` + `apply_native_patch_sides.py`
  （schema types/graph、BAI v15、supplementary data、threadconnector）。
- 已核：原 `/root/heroes3-ai-lab/src/gym/vcmi/rel/bin/libmlclient.so` 时间戳
  未变（Oct 14 21:29），原运行时不携带本窗口补丁。

## 变更的共享文件

- 无。本窗口只写 `experiments/human-tactics-events-v2/**` 与隔离运行时。

## 交接/续作提示

- 训练入口：`run-bc-cuda.sh`（gpu-venv）；评估：`run_pilot_events.py --policy model`。
- 后续建议：普通战斗保留集评估需按主协议开发集执行（本窗口未执行，见
  STRATEGY_INTERFACE_CONTRACT.md 第 4 节）。
