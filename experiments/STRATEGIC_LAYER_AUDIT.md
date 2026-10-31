# 大地图/完整对局接口审计（2026-10-17）

目标：为战略层建立最小可执行闭环。本文只记录**实际运行验证过**的事实，不含推测。结论：**闭环尚未打通，卡在一个具体的、可定位的原生代码门槛上**，不是算法问题。

## 1. 结论先行

|问题|实测结论|
|---|---|
|vcmi-gym v15 是否支持大地图|**不支持**。`connectors/v15/` 内 grep `adventure|endTurn|moveHero|newDay` 零命中；`envs/` 只有 v13/v15 战斗环境|
|VCMI 原生能否无头跑完整 AI 对局|**能**。`vcmiclient --headless --testmap <map> --ai A --ai B`，`--headless` 隐含 `--onlyAI`|
|可用的原生战略 AI|仅 `Nullkiller2`（真实战略 AI）与 `EmptyAI`（只结束回合）。战斗 AI 有 `BattleAI`/`StupidAI`/`MMAI`|
|现有地图能否直接用于完整对局|**不能**。全部 535 张 `.vmap` 都是战斗夹具|
|自造核心英雄地图是否可行|**可行**，已生成并成功初始化完整游戏状态|
|是否已经打出完整对局|**没有**。卡在 ML 服务端插件的一条硬抛异常|

## 2. 无头完整对局入口（已验证）

`vcmiclient` 的相关选项（实测 `--help`）：

```
--headless          runs without GUI, implies --onlyAI
--onlyAI            all players will be default AI
--ai arg            AI for the player, repeatable for consecutive players
--testmap arg       start a specific map
--spectate          spectator interface for AI-only games
```

`--testmap` 的资源名规则：必须带 `Maps/` 前缀且不带扩展名，例如 `Maps/diverse-192`。
写成 `lab/diverse-192.vmap` 会报 `Resource with name LAB/DIVERSE-192 and type MAP wasn't found`。

## 3. 阻塞点：ML 服务端插件拒绝非战斗对局

运行到完整初始化后，启动被拒绝：

```
Gamestate initialized!
Failed to launch game: Cannot track stats when randomHeroes is disabled
```

来源：`src/gym/vcmi/server/ML/ServerPlugin.cpp:346 InitStats()`，在 `ServerPlugin` 构造函数初始化列表中无条件调用（同文件:381）：

```cpp
if (config.statsMode == "disabled")
    return nullptr;
if (config.randomHeroes == 0)
    throw std::runtime_error("Cannot track stats when randomHeroes is disabled");
```

`config.statsMode` 来自 `server/ML/Config.h:61` 的 `settings["server"]["ML"]["statsMode"]`，默认值 `"red"`。

**为什么改配置无效**（三条都实测过）：

1. 写 `<worker>/data/vcmi/config/settings.json` 的 `server.ML.statsMode=disabled`：启动日志里的 settings dump 完全没有 `server.ML` 节点，值被丢弃。
2. 根因：`config/schemas/settings.json` 里 `server` 声明了 `"additionalProperties": false` 且**没有 ML 属性**，未知键在加载时被剔除。
3. 把 schema 复制到 worker 私有目录并补上 `ML` 属性后重试：仍然抛同一异常。说明服务端进程读的不是这份配置。
4. 停用 `ml` 模组（`core`+`vcmi` 预设）后重试：异常**依旧**。因为 `libmlserverplugin.so` 是静态链接进服务端的，与模组开关无关。

由此可以解释一个更早的疑点：项目文档里长期记录"tight 阵型参数没有透传到 worker"——如果 `server.ML` 一直被 schema 丢弃，这类参数本来就到不了服务端。

### 3.1 真正的传递路径（最后定位）

`server/CGameHandler.cpp:613`：

```cpp
ML(mlplugin = std::make_unique<ML::ServerPlugin>(this, gs.get(), si->mlconfig));
```

ML 配置根本不经 `settings.json`，而是随 `StartInfo` 一起从客户端传到服务端。`--testmap` 走的是默认 `mlconfig`，因此 `randomHeroes=0`、`statsMode="red"`，必然触发异常。这也解释了为什么改 settings、改 schema、停用模组三种办法全部无效——它们都作用在错误的通道上。

同一构造函数里还有第二个隐患：

```cpp
stats(InitStats(gs, config, heropools.at(0).size(), 2*heropools.at(0).begin()->second.heroes.size()))
```

`heropools` 由 `InitHeroPools(gs, config)` 构建，只有 ML 战斗地图才定义英雄池。普通冒险地图上 `heropools` 为空，`.at(0)` 会抛 `std::out_of_range`。

结论：**不是一条 `throw` 的问题，而是整个 ML 插件被无条件构造**。任何只补 `throw` 的补丁都会在下一行继续崩。正确做法是让冒险对局使用一个不构造 ML 插件的服务端（`ENABLE_ML=OFF` 构建），或用独立的 `mlconfig` 通道显式传入禁用值——两者都需要构建，不能靠配置绕过。


## 4. 地图：从战斗夹具派生可用的大地图

`lab/*.vmap` 其实是**真实的 72×72 冒险地图**，不是纯战斗文件：

- 2 个玩家（red/blue），各 2 名英雄
- 8 座城镇（`owner` 已指定）、1 个 `creatureBank`
- 英雄在 y=2、城镇在 y=70，双方镜像对峙
- 对象带真实坐标 `x/y/l`，地形为完整 `surface_terrain` 网格

唯一的问题是英雄模板用了 `ml:hero_*`（`options.type`），这会把 ML 插件带进来。

`experiments/make-adv-map.py` 已实际生成 `Maps/adv/adv-arena-01.vmap`：只改英雄身份为 core 英雄（`core:christian`/`core:tyris`/`core:orrin`/`core:valeska`），军队、坐标、城镇、地形、胜负条件全部不动。

验证结果：该地图能通过 VCMI 全部加载与校验阶段，走到 `Gamestate initialized!`，随后仍被第 3 节的统计异常拦下。**这证明地图本身有效，阻塞与地图无关。**

## 5. 为什么不就地重建

`src/gym/vcmi/rel/` 是现成的 CMake/Ninja 构建目录（712 个 `.o`），改一行 `throw` 为 `return nullptr` 即可解锁。但实测 `ninja -n vcmiserver` 会连带重建 `bin/libvcmi.so` 与 `bin/libmlserverplugin.so`：

```
[3/5] Linking CXX shared library bin/libvcmi.so
[4/5] Linking CXX shared library bin/libmlserverplugin.so
[5/5] Linking CXX executable bin/vcmiserver
```

这两个 `.so` 的 SHA256 已被冻结进所有正式战斗评估的 provenance（`evaluation-provenance-runtime-contract.json` 等）。就地重建会让已发布的 3072 场正式结果无法再被校验。**因此不能在 `rel/` 里重建。**

## 6. 下一步：可执行的解锁方案

### 方案 B（推荐）：不含 ML 插件的服务端

`ENABLE_ML=OFF` 构建 `vcmiserver`，插件根本不存在，`CGameHandler` 的 `ML(...)` 分支为空。这同时消除了 `heropools.at(0)` 的隐患，是唯一不需要理解 ML 内部状态的干净解。产出的服务端与战斗侧完全隔离，冻结 SHA 不受影响。

### 方案 A（次选）：隔离构建 + 完整补丁

新建 `src/gym/vcmi/rel-adv/`，构建时保留 ML 但把插件构造包在"是否 ML 对局"的条件里（同时处理 `statsMode` 与 `heropools` 两个分支）。比方案 B 复杂，只有确实需要在冒险局里复用 ML 组件时才值得。

### 方案 C（不建议）

就地打补丁重建。会让冻结 SHA 失效，破坏可复核性。

## 7. 里程碑定义

|阶段|状态|
|---|---|
|M0 无头客户端能加载冒险地图并初始化完整游戏状态|**已达成**（`Gamestate initialized!`）|
|M1 原生 AI 双方跑完完整对局并产出原生胜负|**未达成**，阻塞于第 3 节|
|M2 我方策略接管一方（战略层），另一方仍用原生 AI|未开始|
|M3 结构化整局轨迹（观测/候选/动作/引擎结果/资源/兵力/胜负）落盘|未开始|
|M4 与原生 NKAI 及简单基线做同图同种子对照|未开始|

## 8. 本次新增文件

- `experiments/make-adv-map.py` — 从战斗夹具派生核心英雄冒险地图（已运行，产出 `Maps/adv/adv-arena-01.vmap`）
- `experiments/adv-run.sh` — 无头完整对局 harness（含配置隔离、私有 schema、日志提取）
- `experiments/adv-smoke.sh`、`adv-try-names.sh`、`adv-scan-maps.sh`、`adv-inspect-map*.sh`、`adv-log*.sh` — 审计过程中实际使用的探测脚本

## 9. 不能宣称的

- 不能说已打通完整对局闭环：目前只到状态初始化。
- 不能说已有战略层策略：一行策略代码都还没有，`Nullkiller2` 是原生 AI，不能算自研成果。
- 不能说大地图接口"已支持"：当前构建在服务端层面是战斗专用的。
- 主动英雄魔法、兵链、经济、飞跳回仍全部未完成。
