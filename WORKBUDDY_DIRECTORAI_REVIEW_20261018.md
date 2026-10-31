# DirectorAI只读代码复核：M2下一步优先级

2026-10-18。已实际读取隔离源码和Lab内脚本/报告；没有编译、运行游戏或修改WorkBuddy的实现。以下是建议其继续修复的具体问题，不是已经修好/已经复现崩溃根因的声明。

## 1. 先初始化基类cbc，不能仅初始化自定义cb

`src/vcmi-adv/AI/DirectorAI/CDirectorAI.cpp::initGameInterface`只设置自己的cb、env、autocombatPreferences和playerID，没有设置继承自CAdventureAI的cbc。当前DirectorAI也没有initBattleInterface覆盖来保存它。

`lib/callback/CAdventureAI.cpp::battleStart`先assert(cbc)，随即`suspendWaitTillRealize()`解引用cbc->waitTillRealize。Release下断言关闭不会防止空指针访问。

同一源码树`AI/Nullkiller2/AIGateway.cpp::initGameInterface`则明确`cbc = callback; cc = callback;`。优先按基类协议补齐初始化并对当前实际指针做日志/运行校验；不要为了消除异常把断言或回调检查去掉。具体此次core是否落在这里仍要用调用栈证实。

## 2. 当前找敌人的代码实际上取不到敌人

实核`lib/callback/CPlayerSpecificInfoCallback`：

- `getHeroesInfo()`只返回本玩家playerState->getHeroes()。
- `getTownsInfo(bool onlyOur = true)`默认只返回己方城镇；false才返回可见城镇（不是全图未知城镇）。

DirectorAI::findTarget遍历getHeroesInfo再排除己方，敌英雄候选因此为空；随后遍历默认getTownsInfo再排除己方，敌城镇候选也为空。仅看到一条MoveHero日志不证明动作由DirectorAI发出，应关联请求player/hero/requestID，可能是Nullkiller2的动作。

修为玩家可见对象的合法枚举/记忆接口；不要为了取到敌英雄直接访问服务器全图。没有已知敌人时，后续要允许合法探索/资源目标，不应一直结束回合。先做可见敌人存在、隐藏敌人不存在的最小验证。

## 3. heroMoved不是完整移动请求已结束的充分条件

过滤对方英雄事件是必要检查，但不能保证整个异步协议正确。当前pendingMove在cb->moveHero之后才置true，可能漏掉立即回调；仅一个bool不能关联具体hero、request和turn，也不能区分中途移动、阻挡、战斗、交互、死亡/易主。

建议记录稳定hero ID和请求生命周期，在发送前置pending，按当前玩家/有效回合/对应请求处理回调。不要在全局事件回调内递归不断issueMove或提前endTurn；以受控执行器/状态机处理Idle、AwaitMoveResult、Query、Battle和TurnEnd，并参考原生AI的等待/线程机制，避免在处理网络事件的线程阻塞等待自身回调。

先保存此次core对应的原生调用栈和版本；必要时在隔离环境加调试符号/空指针日志。一次只改变一个已定位因素，保留失败日志。基于“可能”反复改回调不算定位完成。

另外，当前CCallback::moveHero实现是封装MoveHero请求；默认EPathfindingLayer::AUTO与代码中的assert存在需要核对的调用约束。不能仅凭方法名断言它一定会为任意远处目标计算完整合法路径，检查原生调用示例、layer、请求失败回复及路径接口。

## 4. harness的AI参数尚需接通

实读experiments/adv-run2.sh：AIONE/AITWO仍只传给`--ai`，未见把它们导出到`LAB_ADV_AI_<slot>`。既然此分支--ai已确认不消费，仅修改Client读环境变量不等于脚本参数生效。

在harness中明确按玩家slot传递期望AI，记录实际分配，若实际AI不匹配就判测试无效而不是悄悄跑NKAI对NKAI。用脚本命令即可复现，不能依赖交互shell中残留的LAB_ADV_AI变量。

## 5. 立刻改为每局独立证据目录

adv-run2.sh当前固定workers/adv-run2并每次rm -rf该目录；后续复跑会覆盖client.log、core、存档。M1_EVIDENCE.json有日志SHA但没有各次原始日志的唯一存储路径。请先确认完整日志是否已另行归档；如果没保留，明确这个证据缺口，不称原始日志仍可独立复核。

每局使用唯一run_id，固定保存命令/环境白名单、地图/二进制/源码SHA、配置、退出码、原始完整日志、原生胜负、行动/回合摘要和存档。不要递归删除上一次worker目录。核心日志中时间戳不同，不足以证明所有行为差异只来自时间戳。

同seed同胜方同天数支持终局层面的重复，不等于逐动作确定性已经成立；后续比较规范化动作/状态摘要再升级这一结论。发现超时/崩溃仍单独计，不计为胜利。

## 修复后的验收顺序

1. 初始化/可见性/AI分配最小检查通过。
2. DirectorAI对EmptyAI、DirectorAI对Nullkiller2，两种角色都能正常推进、触发并结束战斗、继续冒险和正常终局，保留崩溃样本。
3. 固定种子重复，再换种子及位置。能够赢不是先决条件，但不能靠一直endTurn假装有策略行动；报告目标、路径和由本策略发出的合法动作。
4. 在这之后再接建设、招募、探索、经济及目标价值，逐步建立整局轨迹和基线。竞技场派生图只用于协议测试，不当战略水平基准。

M1是重要的原生完整对局基线，M2仍待以上实测。不要把Nullkiller2获胜、自研AI被选中或库编译成功当作自研策略已经完整可玩。
