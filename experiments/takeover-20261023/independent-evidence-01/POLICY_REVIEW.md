# 招募 policy-v2 / run-v1：执行前独立审核

最终内部质量门禁通过。SOURCE_FREEZE.json SHA `9919de90735e946dbb543059923287f0c0e712ee0a91a2d09cc5e47195890a22` 所列24文件逐字节一致，独立 CPU 审核所读全部 policy/run Python 源快照在审核后仍精确匹配。证据为 POLICY_FINAL_FREEZE_AUDIT.json、POLICY_CPU_AUDIT.json。本审核未改 policy/run/native 源或任何原始证据，未取得资源锁，0 native、0 GPU 调用、0 optimizer steps。

实际重新读取机制资格与原生 runtime catalog（150 species、227 candidate width），CPU 加载 b9ede 初始化及真实 833 父权重。所有旧模型 state tensor 逐位继承；新招募 residual 为零、recruit_bias=-4 属手工初始值。对全部17真实机制请求独立执行两次 CPU forward，logits/value 逐位一致；移除招募候选后的同一请求投影与旧833 logits/value逐位相等。未将脚本机制选择、合成 catalog 或 CPU 网络检查当作招募训练/专家。

CPU codec 保存/读回明确标记 cpu_codec_test，创建的 Adam 为空且未 step；坏 Python RNG、CPU RNG 长度、Adam counter、参数顺序、LR、partial boundary、模型 shape、人工坏 moment shape 共8类负例全部拒绝且 live model/Adam/CPU RNG/Python RNG 不变。真实 CUDA 的 model/Adam/moment/counter/CPU-CUDA-Python RNG 恢复尚须新学习器实际执行验证，CPU codec 不替代它。

两 collector 真实调用各自准备流程、生成隔离地图/config/908项输入冻结后，以审核专用替换在 owned_resources 之前硬停止，未进入资源竞争或原生/GPU调用。修复了最初 DEV collector 的未定义 DEV_TOOLS；仅 py_compile 无法发现该入口错误。

已逐源码确认 sealed admission 要求 schema6/实际 catalog/full state 事务及真实 CUDA action/logp/value/采样 Generator 初末 RNG 精确重放；normalized events 与真实 typed 相等，sealed loader 重新核验 raw/source/collection hash 链。坏 RNG/Adam 在 scratch 对象上预检后才允许污染 live 状态。optimizer ID 唯一、state subset、协议 LR、模型 shape 和参数顺序均有门禁。

八 TRAIN cells 固定训练地图、双角色、EmptyAI/Nullkiller2、seeds3900..3907，一次有限更新；硬 pin 登记初始化 b9ede，weights-only 833、新 Adam/RNG、不接旧 rollout，至少一个真实执行招募样本才准更新。十六 DEV 为两模型各八个4000..4007配对局，使用 DEV 地图/双角色/两对手与 CPU argmax，不进入训练。两入口均先 GPU lock 再 pool lock；冻结源和 capsule、原始输入在运行前后检查。名称残留 v5 文件不等于运行 schema5；实际所有动作/响应/epoch 门禁为 v6/v3 招募路径。

报告观测已补招募 actor/critic 新分组 delta/Adam 步、recruit_bias、实际招募与桶/资源/兵力及 TRAIN 信用统计。必须等真实训练、保存加载与独立配对 DEV 后才能判断收益；此处仅放行已登记的有界执行，不升级模型或宣称学会招募。
