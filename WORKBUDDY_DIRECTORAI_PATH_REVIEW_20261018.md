# DirectorAI 移动补充复核（2026-10-18）

只读核对共享 DirectorAI/harness/status，以及 WSL 隔离源码；未修改活动代码或启动对局。M2 尚未通过的判断合理。

## 1. 坐标差异不能直接归因于读取时机

实际隔离源码 `lib/mapObjects/CGHeroInstance.cpp:159–167` 明确：

```
convertToVisitablePos(position) = position - getVisitableOffset()
convertFromVisitablePos(position) = position + getVisitableOffset()
```

因此 `(4,2)` 与 `(5,2)` 可以是英雄访问格与对象锚点的正常差异，不足以证明位置过期。实际 `AI/Nullkiller2/AIGateway.cpp:1099,1152` 在发移动请求前使用 `heroPtr->convertFromVisitablePos(dst)`。

不要全局将 visitablePos 替换为 pos。目标选择/寻路统一使用其接口约定的坐标；发送请求时转换为该移动英雄的对象坐标；TryMoveHero.start/end 比较也须统一坐标系。先对一个英雄记录 pos、visitablePos、offset、转换结果，验证往返恒等。英雄丢失后应通过 ID 重新取对象并判空，不能继续解引用旧指针；这与坐标转换是两件事。

## 2. 寻路与异步完成

`CCallback.cpp:29–42` 两个重载都只打包路径并发送，没有本地寻路。改成 vector 并不自动保证节点顺序、坐标、层和可达性正确。

建议先参考现有 NKAI 的 getPathsInfo/getPath + 按相邻节点逐步移动实现。只先做陆地无传送的小测试，取本回合可达的下一节点，显式转换坐标。不要第一版直接发送整条多步路径：heroMoved 是逐步事件，当前 pendingMove 在第一次回调就清空并重发，可能与剩余路径重叠。

零位移是防死循环条件，不能普遍当作动作失败。NKAI 源码明确 BLOCKING_VISIT / BATTLE 可发生有效交互而不抵达格子。应分别记录位移、移动力消耗、战斗/访问/目标所有权变化。一次受阻后可选择其他可达目标/英雄，不要长期每天重复同一失败目标。

## 3. harness 尚未真正强制校验

当前共享 `adv-run3.sh` 仅 grep/打印实际 AI 分配，没有比较预期与实际并据此失败；末尾 echo 也会覆盖游戏进程退出状态。需要结构化结果记录 engine_exit、AI 分配、原生终局、崩溃/超时，并明确脚本退出码。gdb 自身退出码不能代替 inferior 状态。

RUN_ID 只精确到秒、mkdir -p 允许重用；同秒同配置可能覆盖。使用 mktemp 或纳秒加随机后缀，并拒绝复用目录。

## 4. 下一次最小验收

先通过相邻空地一步、绕障碍多步、阻挡访问/战斗三个受控案例，再跑 DirectorAI 双角色完整对局。日志应能复算目标、合法路径、执行步、实际进展、失败原因；不以胜利作为协议通路的必要条件，不以请求数量或进程正常退出代替有效推进。训练继续保持不启动。
