# 同数据终局目标探针：预登记96局DEV

方法只由TRAIN终局系数及已观察片段诊断选择，没有用DEV作为教师。生产探针先精确复现旧candidate62的模型/Adam/四RNG/计数，随后从相同完整61状态重放同一512真实on-policy记录，唯一改变253条末尾片段的目标，两分支各128实际Adam；MC累计7936。新原生训练0；MC完整CPU/CUDA模型/Adam与四RNG恢复通过。

固定三模型：既有parent60、旧candidate-micro62(lambda.95终局延伸，评估标签control)、MC62(评估标签candidate)。control不是旧的无延伸control62，也不是control68。此处严格比较同源62，不混用不同恢复目录。新模型SHA5cd856b3…310354，旧62 SHAec26fe4b…fd0eec。

DEV沿原地图192..199×双方×BattleAI/原作者CPU ONNX MMAI，各模型32局，共96；新seed固定2026109400+scenario_index*100。同格共享seed，CPU确定性推断，8并发沿已资格化评估容量。完整正常终局、实际每步请求/响应/图/动作证据、shutdown/原始哈希重审与全部CPU logits/value/probability重算；不追加、不重播种、不择模，不把公开前缀相同说成隐藏状态完全相同。

已有DEV地图曾使用过，只是本epoch的seed新；这是开发方法探针，不是最终测试或稳定总体胜率认证。任何工程无效停止并保留，不能记作输局或重跑。无训练/专家准入，无自动模型晋升，finaltest封存。

严格GPU锁→pool锁、非阻塞；两真实fd继承各独立worker会话，pool fd/inode验证沿原资格门。每局超时300秒后清理该进程组，控制器中断会停止全部自己创建的会话；正常返回也核验组无残留。批次前后资源门>2GiB、swap<256MiB，首批前>4GiB；单组8原生CPU推断，无GPU学习器和重CPU分析交错。
