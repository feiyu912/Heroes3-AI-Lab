# 隔离战略运行时：保存与恢复接口审计

审计日期 2026-10-18。以下均直接读取 WSL 的 `/root/heroes3-ai-lab/src/vcmi-adv/`，不是 Windows 上游副本。初始审计只读；随后获主窗口授权，已仅应用下述 testsave 终局退出条件修复。未改 DirectorAI 或 runner，未构建，未启动游戏。

## 结论

**已有实际消费的 `--testsave` 无头加载入口，不必新增 CLI。** 当前保存是单个二进制 `.vsgm1`，不是 ZIP，也不需要 `.vsgm2`。此版本资源类型只注册 `.VSGM1`，不能把寻找 `.vsv` 当作判断“没有保存”的依据。

原生命令形态，在相同构建与依赖、独立 XDG 目录下：

```text
vcmiclient --headless --testsave Saves/takeover-resume-snapshot --nointro --disable-video
```

物理文件放在 `$XDG_DATA_HOME/vcmi/Saves/takeover-resume-snapshot.vsgm1`。参数是资源名，不是任意物理绝对路径；使用 `Saves/` 前缀、不带扩展名，避免依赖隐式路径猜测。不要同时传 `--testmap`，其分支优先，会启动新游戏而不是恢复。

## 已追踪到的调用链

| 入口 | 实际隔离源码位置 | 行为 |
|---|---|---|
| `CCallback::save(fname,notifySuccess)` | `lib/callback/CCallback.cpp:322` | 发 `SaveGame` 原生请求 |
| 保存包执行 | `server/NetPacksServer.cpp:32` | 调 `gh.save`，但无论内部是否捕获异常都设置 `result=true` |
| 原生写盘 | `server/CGameHandler.cpp:1829` | 创建 `.vsgm1`；依次保存 CGameState 与 CGameHandler |
| 文件头 | `lib/serializer/CSaveFile.cpp:16` | `VCMI` + 4 字节序列化版本 + `VCMISVG` |
| CLI 声明 | `clientapp/EntryPoint.cpp:176` | 注册字符串参数 `testsave` |
| CLI 消费 | `clientapp/EntryPoint.cpp:396` | 写 session.testsave、onlyai=true，调用 `debugStartTest(...,true)` |
| 加载启动 | `client/CServerHandler.cpp:966` | LOAD_GAME，`CMapInfo::saveInit(ResourcePath(...,SAVEGAME))` |
| 保存元信息读取 | `lib/mapping/CMapInfo.cpp:53` | CLoadFile 读取地图头及 StartInfo，构造资源 URI |
| 真正状态加载 | `server/CGameHandler.cpp:1876` | `gs->loadGame(lf)` 后加载 handler，重建运行时数据 |
| 客户端恢复 | `client/Client.cpp:115` | 使用网络传来的恢复状态，重新创建 map handler、玩家环境与 AI 接口 |
| 资源路径 | `lib/filesystem/Filesystem.cpp:190` / `lib/VCMIDirs.cpp:26` | `SAVES/` 映射到 `userDataPath()/Saves` |
| 格式注册 | `lib/filesystem/ResourcePath.cpp:128` | `.VSGM1` 是 SAVEGAME |

`startload` 在此客户端/入口源码未找到，不能把其他版本的这个选项当成当前可执行路径。`--savefrequency` 确实消费到 `general/saveFrequency`，但全 AI 路径不保证有玩家界面的日自动保存回调，主动 `CCallback::save` 更直接。

## 需要的最小补丁：只修恢复终局自动退出

`client/NetPacksClient.cpp:472` 当前只判断 session.testmap：

```cpp
if(!settings["session"]["testmap"].isNull() && allPlayersEndedGame)
```

已由幂等工具 `patch_testsave_exit.py` 在隔离源码应用，等待主窗口统一增量构建：

```cpp
if((!settings["session"]["testmap"].isNull()
    || !settings["session"]["testsave"].isNull()) && allPlayersEndedGame)
```

加载本身不依赖此补丁；未补时可能真实正常结算后仍挂着直至 harness 超时。不能把 timeout 124 当作正常退出，也不能用恢复脚本强行抹成 exit=0。补丁只作用于隔离源码，修改后的二进制另记 SHA；若验证完全同构建恢复，应先完成补丁编译再生成保存。补丁后 `NetPacksClient.cpp` SHA 为 `6e10125340aef5965d3e0e29a671264bfdb116c795687d6266290bbf6eb2c3fc`，原 SHA 及处理记录保存在 `testsave-exit-patch-6e10125340ae.json`。

## 保存成功判定不能只看请求返回

`CGameHandler::save` 内部捕获写盘异常不向外抛，`visitSaveGame` 随后仍写 `Game has been saved as ...` 且 `result=true`。因此必须同时看到真正的 `Game has been successfully saved!`、目标文件完整稳定、非零大小、SHA 与合法文件头。`Game has been saved as` 和请求完成回调单独都不足以证明成功。

建议在己方新回合开头、还没有发出移动或访问请求时保存一次，使用 `cb->save("Saves/takeover-checkpoint", false)` 这类带资源前缀且不带扩展名的名称；`notifySuccess=false` 避免 AI 要回复信息对话框。记录保存时的日期、玩家、英雄真实/访问坐标、移动力、资源及军队，随后在恢复后首个可观测状态逐项核对。最好不要在战斗/升级/访问查询中间首次验证保存，因为查询恢复与 AI 异步私有状态需要额外测试。

## 恢复边界与验收

- 保存含地图、StartInfo、完整 CGameState 及服务端状态；恢复沿原生加载流程进行，不是重建一张相似地图。
- 客户端在恢复时重新 `initPlayerInterfaces`。DirectorAI 的 C++ 成员如访问计数、已尝试集合、pending 标志不会自动由这个保存接口恢复，除非策略另用 `saveLocalState` 并实现读回。这意味着“成功恢复游戏状态”不等于“逐动作完全相同继续”。
- 同一源码也不能代替同一二进制。记录保存与恢复双方 client/server/libvcmi 及相关 AI 动态库 SHA、激活模组、配置；避免 ML=ON/OFF 混用。
- `prepare_save_restore.py` 只校验文件头与 SHA、复制到唯一恢复目录、生成命令与带共享锁的启动脚本，**本身绝不启动游戏**。文件头有效不代表完整反序列化已通过。
- 运行后必须出现 `Game has been successfully loaded!`、客户端 `Game loaded, initialize interfaces.`、正确 AI 分配以及后续真实回合行动；首个恢复状态要与保存检查点一致，然后继续到原生终局与正常退出。仅出现加载提示、没有继续行动不算恢复闭环。

准备命令：

```text
python3 /mnt/g/Heroes3-AI-Lab/experiments/adventure-takeover-v5/prepare_save_restore.py --save-file /绝对路径/checkpoint.vsgm1 --source-run /原始唯一运行目录 --red DirectorAI --blue Nullkiller2
```

工具输出新的 `restore-v5-*` 目录。经主窗口协调后单独调用其中 `launch-restore.sh` 才会启动游戏；原保存不改，复制保存 SHA 保持一致。当前审计未声称已生成真实保存或已跑过恢复局。

## 实测恢复失败后的追加只读诊断：invalid 人类槽位

主窗口随后真实产生 337862 字节存档，首次 `--testsave` 运行被 `CVCMIServer.cpp:369` 的人类存活预检拦截：`Human player invalid has no heroes and no towns!`。检查本地隔离源码后，预检应保留，问题在其上游人为产生了 invalid 槽位：

1. 全 AI 存档的 `StartInfo.playerInfos` 只有原来的红蓝 AI，本地真人没有分配颜色。
2. `client/CServerHandler.cpp::debugStartTest` 的 onlyai 分支（约1003行）无条件调用 `setPlayer(myFirstColor())`。`myFirstColor()` 经 `LobbyInfo::clientFirstColor`（`lib/StartInfo.cpp:197`），没有真人颜色时返回 `PlayerColor::CANNOT_DETERMINE`。
3. `LobbySetPlayer` 把这个非法颜色传到 `server/CVCMIServer.cpp::setPlayer`（724行起）。其 `si->playerInfos[clickedColor]` 使用 map 下标，会插入一个根本不在地图上的 invalid PlayerSettings；后续还会给它分配真人连接。
4. 因而服务器正常检查到一个不存在的真人玩家并拒绝恢复。不是地图真的少了玩家，也不能靠删除存活预检“修复”。

最小本因修复如下；随后已获主窗口授权，由幂等 `patch_testsave_human_guard.py` 应用到隔离客户端，正常真人等待循环保持不变，server 预检未改：

```cpp
if(settings["session"]["onlyai"].Bool())
{
    const auto humanColor = myFirstColor();
    if(humanColor.isValidPlayer())
        setPlayer(humanColor);
    while(myFirstColor() != PlayerColor::CANNOT_DETERMINE)
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
}
```

另一个合理的防御修复是在服务端 `setPlayer` 最前先校验 `clickedColor.isValidPlayer()` 且在 `playerInfos` 中存在，再取 `.at` 或迭代器引用；不要让非法网络/调试请求插入新玩家。客户端 guard 是这条实测路径的最小修复，不需绕过游戏合法性判断。

恢复后还要检查是否真实进入后续回合：修复本启动阻塞不等于已经完成状态恢复与终局验收。

## 实际恢复闭环已独立审核通过（仅限回合起点）

主窗口统一构建并真实运行后，本窗口只读审核两份完整原始日志、计划、存档、策略轨迹：

- 原局：`economy-transfer-v5-2026101801-sz4jx0ho`。
- 恢复局：`restore-fixed-v5-2026101801-xoj9sx1q`。
- 原存档与恢复复制件均为 337862 字节，SHA `55363916016be15e22f277c8c14725acff46a5c5916bf1e3d4e14d2aea8ee71e`。
- 三个 LOAD_GAME 标记从恢复原始日志实读均出现；双方记录的 client/server/libvcmi SHA 相同。
- 初始可见状态相同，57 条策略状态记录逐字节相同，SHA `0ace582dd006be13710e9a5ba1b4b989400b5a9df566eb1572f67a8ffbf1fd84`。另外逐条提取的 134 条 DirectorAI 移动结果文本序列也相同。
- 两局均原生 15 天、蓝方胜、exit=0，成功移动 134、失败 0。
- 双局各独立核实 5 次建设、4 次招募、4 次转移的真实状态变化；不是只数成功回调。

证据是 `ECONOMY_RESTORE_AUDIT.json` 与 `ECONOMY_RESTORED_STATE_AUDIT.json`，审计工具为 `economy_audit.py`。guard 文件 SHA `00aec05dc1d74e88cb024e6c5e341aef438bd2a72a469797d735a2078015f229`，幂等重跑 changed=false。

该结论只验证这里的**回合起点存档恢复**。57 条是记录的玩家可见战略状态，并非全部原生事件；AI 私有 C++ 状态仍未序列化，未证明任意局中/异步请求期间恢复。经济接口成立也不证明自研策略学会获胜，本例仍输给原生对手。
