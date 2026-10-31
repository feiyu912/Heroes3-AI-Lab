# 一次未复现的原生堆异常：只读诊断

状态：**已观察到堆损坏，根因未知，未修复**。本诊断未修改引擎/AI/runner，未启动游戏或构建。

`development-01-15-2026101812-7whqgl65` 在蓝方第124天中止，client exit=-6，终局不存在。尾部出现 `double free or corruption (out)` 与 `malloc(): unaligned fastbin chunk detected`，之前是英雄交换任务完成和两次 BuildAnalyzer 更新日志。该失败必须保留为崩溃，不可替换成胜负。

`crash-audit-v5-2026101812-e9jfiqs2` 与 `crash-repeat-v5-2026101812-220p4ie_` 都正常147天蓝胜，393条策略状态轨迹完全相同；原崩溃的334条状态逐条等于正常局前334条。三局计划中 client/server/libvcmi SHA 全部相同，日志 SHA 与原runner记录一致。证据在 `HEAP_FAILURE_LOG_AUDIT.json`，可由 `heap_failure_log_audit.py` 只读生成。

## 具体源码边界与假设

1. `AI/Nullkiller2/AIGateway.cpp:557` 每次 yourTurn 向 AsyncRunner 提交 makeTurn；`lib/AsyncRunner.h` 使用 TBB arena/task_group，并非单任务串行队列。`finish` 中断后 wait，析构先 finish 再销毁 Nullkiller，具有显式等待；不能只凭看到异步代码就断言生命周期释放错误。
2. `Engine/Nullkiller.cpp::updateState` 取得 aiStateMutex 后更新 BuildAnalyzer。`Engine/ResourceTrader.cpp::trade` 也会直接调用同一 BuildAnalyzer.update；makeTurn 尾部的交易调用没有覆盖全方法的 aiStateMutex。如果存在实际重入/重叠，可竞争 developmentInfos.clear/push_back 和 vector 引用。但本三局日志**没有同一玩家同一天重复 makeTurn 起始**，所以特定“重复回合任务”假设目前证据很弱。连续两个更新也可来自顺序调用。
3. BuildAnalyzer 包含 vector/string/资源集合的清空、构建和重排，容易成为更早堆破坏的发现点。allocator 报错所在分配/释放不一定是首次越界/重复释放处。英雄交换刚完成，军队/任务/查询对象过期指针也是候选；没有栈不得归因给 BuildAnalyzer 或英雄交换代码。
4. yourTurn 的 queryID=-1 是当前路径的 sentinel；日志里反复出现 -1 不是“同一真实查询被处理124次”的证据。

## 下一步最便宜的诊断

首选对**固定同构建**的一次真实运行加 gdb SIGABRT 捕获，无需改源码或重编。应保持正常 ASLR（gdb 的 `set disable-randomization off`），防止默认关闭地址随机化改变堆布局；保留所有线程栈、共享库路径和映射。准备好的命令模板 `heap_abort.gdb` 不会自行启动游戏；主窗口可在唯一运行目录、共享资源锁内调用：

```text
gdb -q -batch -x /mnt/g/Heroes3-AI-Lab/experiments/adventure-takeover-v5/heap_abort.gdb --args /固定二进制/vcmiclient --headless --testmap Maps/adv/takeover-economy-36-v1 --nointro --disable-video
```

运行前必须另外设置原种子、AI分配、独立 XDG/config/地图和动态库目录，不能直接在原失败目录启动覆盖证据。模板只用于捕获，不是完整runner，不把 gdb退出码当游戏正常终局。若当前构建已经变化，应另记新SHA，不将其称为同二进制重现。

若又正常结束，最小增量证据是下一轮在函数入口记录线程ID、`AIGateway*`、`BuildAnalyzer*`、当前day和进入计数；只有同地址同时进入才能确认竞争。不要先按假设串行化所有 TBB 工作线程：AsyncRunner 明确要求至少4线程以免阻塞回调死锁。若栈不能定位首次破坏，再考虑独立 ASan 构建（捕 UAF/越界/重复释放），而不是立即在活构建全量开 sanitizer；TSan 应作为明确竞争疑点后的专项工具，不能与ASan混成一轮。

在未再现之前不应声称“已解决内存问题”，也不应把两次正常重跑当作原崩溃无效。
