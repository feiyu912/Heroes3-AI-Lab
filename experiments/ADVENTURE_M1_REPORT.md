# 冒险层构建与 M1 结果

2026-10-18。按方案 B 执行隔离 `ENABLE_ML=OFF` 构建。冻结战斗环境全程未变（5/5 SHA 一致）。

## 结论

|里程碑|状态|
|---|---|
|M0 无头加载冒险地图并初始化完整状态|已达成（此前）|
|**M1 原生 AI 完整对局 + 原生胜负**|**已达成，可复现**|
|M2 自研策略接管一方|**部分**：策略已编译、已被正确选中，但对局在移动/战斗交接处中止|
|M3 结构化整局轨迹|未开始|
|M4 与 NKAI 同图同种子对照|未开始|

## 构建

- 源码副本 `/root/heroes3-ai-lab/src/vcmi-adv`（从 `src/gym/vcmi` 复制，排除 `rel/`）
- 构建目录 `/root/heroes3-ai-lab/src/vcmi-adv-build`，`ENABLE_ML=OFF`，Release，Ninja，8 并发
- cmake 3.31.10（系统 3.22 不满足 MMAI 的 3.24 要求）
- `readelf -d vcmiserver` 确认**不含** `libmlserverplugin.so`
- 日志 `/root/heroes3-ai-lab/src/vcmi-adv-build.log`

### 隔离副本内必须修的三处源码问题

上游是战斗专用分支，关掉 ML 后编译/运行会断：

1. `server/battles/BattleProcessor.cpp`：`gameHandler->mlplugin` 未加 `ML()` 宏保护，`ENABLE_ML=OFF` 时编译失败。用 `#ifdef ENABLE_ML` 包裹。
2. `client/Client.cpp::initMapHandler`：上游为无头战斗写成 `if(!headless || IS_ML)`，关掉 ML 后无头模式永不创建 `CMapHandler`，任何 `GAME->map()` 都抛 `Invalid access to GameInstance::map`。改为始终创建。
3. `client/Client.cpp` AI 选择：`--ai` 参数在本分支是**死参数**（声明但从未读取），AI 名来自 `settings["ai"]["adventureEnemyAI"]`，对所有 AI 玩家相同。加入 `LAB_ADV_AI_<slot>` 环境变量覆盖，实现按玩家指定 AI。

## M1 实测

命令：`bash experiments/adv-run2.sh Maps/adv/adv-arena-01 Nullkiller2 Nullkiller2 240 2026101801`

|种子|天数|胜方|退出码|崩溃|
|---|---:|---|---:|---:|
|无（随机）|91|blue|0|0|
|2026101801|21|red|0|0|
|2026101801（重复）|21|red|0|0|

- 双方每回合正常推进，日志含 `Player 0 (red) starting turn, day 1 … day 91`
- 原生结算：`AIGateway: Player 1 (blue) won. I won! Incredible!` / `Turn nr 91` / `All players have ended the game.`
- 同种子重复 → 同胜方、同回合数，可复现
- 全程 0 次 `Disaster happened`

## M2 现状（未完成）

自研策略 `CDirectorAI`（`experiments/adv-ai/`）已实现并注册：

- 派生 `CAdventureAI`，战斗委托给原生 `BattleAI`
- 策略：选剩余移动力最高的己方英雄，朝最近敌方英雄（无则敌方城镇）移动
- 已验证被正确选中：`Player red will be lead by DirectorAI` / `Player blue will be lead by Nullkiller2`

**但对局会中止**：`timeout: the monitored command dumped core`，发生在一次 `MoveHero successfully applied!` 之后、战斗回合推进过程中。已排除 ML 相关原因（同构建下 NKAI vs NKAI 完整跑完）。

已尝试的修正：把 `endTurn` 从 `yourTurn` 移到 `heroMoved` 回调，避免在移动查询未完成时结束回合。该修正后崩溃点未变，说明原因还在别处（最可能是 `heroMoved` 是全局事件接收器，会收到对方英雄的移动事件，导致在错误时机结束回合；或 `CAdventureAI` 的 `cbc` 在 Release 下为 null 而 `BattleAI` 初始化路径需要它）。

下一步应：在 `heroMoved` 中按英雄归属过滤（只处理 `details.id` 属于本方的事件），并核 `cbc` 是否被客户端赋值。

## 不能宣称的

- 不能说自研策略已能完成对局：它会中止。
- 不能把 NKAI 的成绩算作自研成果：M1 双方都是原生 AI。
- 不能说已支持经济/探索/建城评估：派生地图是开局接触的竞技场布局。
- 未验证存档/恢复：`--savefrequency 1` 未产出 `.vsv`。
- 新构建里 MMAI/BattleAI 已编入，但它们在冒险战斗中的实际使用尚未验证。

## 复现

```
bash experiments/adv-build-configure.sh
bash experiments/adv-build-compile.sh
bash experiments/adv-run2.sh Maps/adv/adv-arena-01 Nullkiller2 Nullkiller2 240 2026101801
bash experiments/adv-verify-frozen.sh
```
