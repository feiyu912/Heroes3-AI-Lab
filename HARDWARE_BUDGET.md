# 本机硬件与实验预算

日期：2026-10-13。所有 GiB 按2^30字节；“32GB内存/16GB显存”为硬件名义规格，实际可用需监测。**预算是资源上限与测量方案，不是吞吐或训练时间预测。**

后续原生构建检查已定位本机Visual Studio 2026、MSVC与自带CMake/Ninja，C++20小程序编译运行通过；官方引擎仍缺依赖，训练fork存在平台限制。详见 [Windows原生验证记录](research/NATIVE_WINDOWS_CHECK.md)。

**最新实测补充：** WSL2匹配训练环境已跑通。在固定20对10弓箭手、无魔法/神经网络的负载中，1/2/4/8worker三次10秒测量的决策速度中位数分别为140.6/267.5/500.2/811.4次每秒；8worker总PSS采样峰值约2.35GiB。详见 [实测报告](research/BENCHMARK_RESULTS.md)。这替代该小场景的未知值，不替代下面对复杂战斗/模型训练的估计预算。

## 1. 实测、理论、估计、未知

| 类型 | 结果 |
|---|---|
| [实测]CPU/RAM | 14700KF，20核28线程，RAM约31.82GiB；查询时可用内存约18.94GiB，随桌面负载变化 |
| [实测]GPU | 5070 Ti，16303MiB，Windows WDDM，610.88驱动；首次查询占用1128MiB |
| [实测]基本计算 | Windows现有torch CUDA12.8支持sm_120；32×32矩阵计算成功，无训练或压力测试 |
| [实测]WSL | Ubuntu22.04/WSL2，GPU可识别，已有CMake3.22.1/G++11.4/Python3.10.12；未安装/验证训练依赖 |
| [实测]存储 | G盘剩余约81GiB，F盘约192GiB；不把F盘游戏目录用作训练输出目录 |
| [理论]CPU拓扑 | Intel规格为8 P-core + 12 E-core，P-core SMT，共28线程；逻辑CPU编号到核型映射本次未查 |
| [未知]核心指标 | 引擎步/秒、战斗重置时间、进程私有RSS/PSS峰值、XL地图缓存、GNN activation显存、决策p95、训练稳定性 |

CPU型号规格参考 [Intel官方](https://www.intel.co.jp/content/www/jp/ja/products/sku/236789/intel-core-i7-processor-14700kf-33m-cache-up-to-5-60-ghz/specifications.html)；GPU软件边界参考 [PyTorch Blackwell支持](https://pytorch.org/blog/pytorch-2-7/) 和 [NVIDIA WSL指南](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)。

## 2. 三套资源配置（待测估计）

| 资源 | A 最小版 | B 标准战斗 | C 战略/完整地图 |
|---|---|---|---|
| 参数 | 0.2–1M | 1–5M，小GNN同预算对照 | 战略1–10M起点，战斗独立冻结 |
| 独立环境 | 从1递增至2–4 | 4–8，验证后试12 | 初始1–2完整地图；局部任务另测 |
| worker内存假设 | 0.4–1GiB/战斗进程 | 0.4–1.2GiB/进程 | 1–4GiB/地图只是容量压力假设 |
| 模拟worker合计 | 0.8–4GiB（2–4个） | 1.6–9.6GiB（4–8个） | 1–8GiB（1–2个） |
| 总任务RAM上限 | 8–12GiB | 14–20GiB | 16–20GiB，地图超限减并行 |
| GPU任务显存上限 | 2–4GiB | 6–10GiB | 8–12GiB，模型轮换不全常驻 |
| 初始rollout/批量 | BC128–512；PPO总512–1024步 | PPO总1024–2048；图batch按节点/边总量 | 宏动作512–1024起点；历史/完整保存按CPU容量 |
| 留给系统/桌面 | RAM至少8GiB并留额外突发余量；GPU至少2–3GiB | 同左；若可用RAM下降主动减worker/缓存 | 同左；不以大量swap维持并发 |

不能从以上worker假设宣称VCMI实际占用就是这些数。进程可能共享只读资源，也可能重复加载与缓存；Windows private bytes/working set与Linux RSS/PSS不能混为一谈。估计超出上限时减少环境或采用精简资源初始化，不能先扩到28环境。

## 3. RAM怎么算

`M_total = M_OS + N*M_worker_private + M_shared_assets + M_rollout + M_teacher_search + M_python + M_margin`。按峰值而非空闲平均；同时记录WSL VMMEM与Linux进程，避免重复计共享页。

[理论算例] 给系统/桌面8GiB、学习器/rollout/IPC6GiB、余量3GiB，余下约14.8GiB给worker。若实测每worker私有0.8GiB，则RAM算术上约18个；**这不是推荐并行量**，CPU/TBB和磁盘/重置可能更早饱和。若每worker2GiB，则只有7个。默认4–8符合可控试验，最终取吞吐拐点。

v15维护者报告单观测常约50–500KB；这是作者报告，非本机测量。按0.5MiB raw计算2048步约1GiB，8192步约4GiB；Python对象、int64索引、两侧轨迹和拷贝会进一步放大。建议raw记录、预分配、有界队列、CPU缓存，按实际分布p95而非平均做限额。[日志](https://smanolloff.github.io/projects/vcmi-gym/)

若将示例“紧凑观测+候选”存成16KiB/条，100k条约1.53GiB；同样100k条按0.5MiB图则约48.8GiB。**两个假设不可混用。** 标准版百万图轨迹可能超本机存储预算，需边收集边抽样/压缩、只保存难例和训练字段，先测每条字节数。G盘建立研究/训练总限额，例如首次20GiB，保留编译产物空间。

## 4. 16GB显存与模型规模

[理论] FP32 Adam常见基本项：参数4P、梯度4P、两个moment8P，约16P字节；1M约15.3MiB，5M约76.3MiB，10M约152.6MiB，50M约763MiB。混合精度可能另有master weights，不应简单按半精度把全部除2。以上不含激活、图边消息、optimizer实现临时量、CUDA context、allocator缓存与rollout。

因此主要风险不是1–5M权重，而是大量图关系与缓存。例如2M条边×128维×2字节，单份消息约488MiB，多层反传/中间特征倍增；这是算例而不是v15实测。按图节点/边数量划分mini-batch、grad accumulation、必要时重算，避免按固定图数量批次造成峰值失控。

小模型CPU batch=1通常值得优先测；训练期间中央GPU推理批量8/16/32作为候选，以最大等待1–5ms作为实验参数，记录队列延迟。不要为了GPU利用率把模型盲目放大。GPU低利用可能是环境不足、图构建、Python IPC或批量碎片，需要阶段计时。

训练使用AMP前检查溢出/NaN和动作分布一致；不为5070 Ti下载不必要的巨大CUDA工具链。现有Windowstorch为nightly，正式实验应固定经过依赖验证的环境，特别是torch_geometric扩展、ONNX和Python ABI。本机Windows基础GPU成功不代表WSL训练依赖成功。

## 5. CPU与P/E-core调度

先让系统默认调度作对照，再比较P-core worker、混合核worker；实测映射后设置亲和性，不能假设逻辑0–15必为P-core。P-core优先给延迟敏感搜索/主线程，E-core可承担采样/编码/日志，但E-core worker拖慢同步向量批次可能产生尾延迟。

每worker推理/BLAS/ONNX线程起点1，限制TBB总并发；8worker×每worker28线程会严重超订阅。编译与训练分开，首次编译并行4–8按RSS调整。中央learner保留CPU核处理batch，不将全部物理核占给环境。Windows affinity 与WSL内部核映射不一定能直接等同P/E物理分配；验证困难时用并发限制与默认调度更可靠。

## 6. Windows与WSL2

推荐训练在WSL2 Linux，游戏运行/体验可在Windows。源码、构建、数据缓存放WSL Linux文件系统，G盘用于报告/成果导出；不要把频繁编译与小文件采样默认放/mnt/g。跨文件系统与跨OS每步通信须避免；训练引擎与Python在同一WSL内。

可考虑WSL RAM上限20GiB、适量swap作突发缓冲，但当前没有改.wslconfig。真实负载若持续换页则降低并发，不能把磁盘当等价RAM。WSL预算要包含在物理32GB里，与Windows任务不能各自独占20GB。LinuxGPU由Windows驱动提供，不在WSL安装独立Linux显示驱动；参照官方指南配置。[NVIDIA](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)

Windows原生VCMI构建有官方文档，适合部署；Gym原生移植需pybind/DLL路径、spawn和进程初始化验证，初期不同时维护两套训练平台。[VCMI Windows构建](https://github.com/vcmi/vcmi/blob/0883081b31dc97f326075f7b0326abaa8161b18e/docs/developers/Building_Windows.md)

## 7. 吞吐测量与云算力触发

下一阶段轻量测量序列：单进程固定战斗 → 1/2/4/8worker（12仅当前轮合格后）→ CPU/GPU推理 → 真实奖励/教师搜索；每点先预热，再最多60秒计时，至少3次重复。分别记录启动/重置、规则step、编码、IPC、推理、训练更新与全循环steps/s，不用纯网络forward的速度代表训练。

`T_cycle = T_collect + T_update + T_eval_share`，非异步情况下采样与学习时间相加；环境steps、双方决策数、英雄施法子动作和完整战斗数要分别统计。时长估计等测出有效吞吐再用`目标样本数/实测速度`，评测/重置/异常另计。

优先本地完成中期。若增加worker后GPU仍闲且CPU/环境饱和，第一笔外部资源更可能是云CPU采样/离线教师；若GPU持续算力饱和且小图/小模型仍不足，才考虑GPU；若只是RAM/轨迹膨胀先精简缓存。云环境数据/引擎版本与资产准备另有成本；本次不采购、不启动实例。
