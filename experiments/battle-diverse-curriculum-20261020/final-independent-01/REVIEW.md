# 独立最终复核

本轮工程与真实学习通过，能力没有提升，不升级B64。权威复跑输出为`actual-review-02/AUDIT.json`；01为增加显式DEV模型身份绑定之前的审核中间结果，不作为当前脚本复跑证书。最终checkpoint SHA为`dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa`。

亲自CPU重跑：488冻结输入SHA、全部30 checkpoint与rollout绑定、逐参数差值、每轮Adam载荷/真实计步记录一致性、最终model+Adam加载、15360行合法动作索引与GAE末步bootstrap、phase片段重建、240真实TRAIN槽位各64行/60图、64DEV原始JSON与日志镜像/normal终局/真实shutdown/模型与固定原作者CPU ONNX身份、32对统计。实际计数是3840次CUDA Adam，551正常训练终局370胜、0cut；本独立检查本身0optimizer/0GPU/0native。原训练期间readback与概率重算记录及保存的RNG载荷已核，未独立重演CUDA RNG恢复或全批网络概率。

最终182张量变化、464冻结张量未变；actor heads L2=.187488，last graph=.091594，critic heads=.245884，总L2=.322490。这些参数组都有真实变化，不能把无提升解释为没有梯度更新，也不能仅凭critic参数delta较大重启已被真实梯度机制反证的critic主导假说。

DEV BattleAI12/16→12/16，平均损兵91.125→94.8125；公开作者MMAI11/16→10/16，损兵100.375→101。唯一胜负翻转是作者scenario193防守：B64胜/41动作/损兵130，更新后负/23动作/损兵153。BattleAI197防守仍胜，但损兵74→131，显示只报胜率会遗漏代价。20/32对public graph digest变化；没有每步DEV obs/action，因此不能定位首次政策分叉或断言某种动作导致失败，更不能声称全世界确定性。不同实验DEV种子不同，不能跨批胜率直接比较强弱。

覆盖改善是真实的，但转移曝光平衡不等于终局分布平衡。家族0..5终局数61/78/109/106/93/104，胜53/61/69/67/72/48；BattleAI345终局260胜，对作者206终局110胜。双方各7680行却有不同终局频次，重复快速局给更多终局奖励。`SLOT_TERMINALS.json`进一步反证“难格未完成一局”：240格中0终局=0、1终局=55、至少2终局=185；作者51格只一局，BattleAI只有4格。每格至少一局的下一门禁本批已满足，不能把它作为解释失败的新干预。

15次phase关闭共229个后续未完片段，含3313条已采样行（21.57%）。这些行已以真实next_value参与GAE，关闭不是额外transition、cut或负奖励；0cut不等于没有工程中止的后续battle。它支持调查episode边界调度与bootstrap依赖，却不证明缺少任何格的终局反馈，更不证明这是DEV负翻转的因果。

下一TRAIN单因素候选是保持同样父模型/Adam、奖励与优化器，仅把固定64行强制轮换改为真实episode-boundary轮换，并显式有限总transition/墙钟预算；实际case曝光可能随局长改变，必须预登记和报告，不能伪称仍严格240格各64行。先完成恢复资格与逐步DEV证据，再启动；不从较差结果反复reset B64多pilot，不把DEV193直接变课程、不降低criticcoef。当前证据不足以承诺该干预改善。

记录的最低MemAvailable6696.17MiB、最大模型GPU峰值395.20MiB均来自运行报告；独立一次进程资源快照另在`monitor-independent-01`，未将phase启动的11个worker瞬间冒称16个同时资源测量，也没有声称24并发。保存/续训边界详见`RESUME_READINESS.md`。

## 实际学习幅度补查

`learning_magnitude.py`亲自CPU比较每个保存rollout首16条TRAIN状态，共480条、覆盖60图；这是预固定抽取规则，不是全15360行统计。B64与final argmax改变12/480（2.5%），KL均值.006000、中位.000124、最大.197804；采样动作绝对logp变化均值.046831、中位.000601。float32计算个别KL最低约-4.93e-7属数值舍入，不是负真实KL。最终仍接近原策略的大部分选择，但变化确实存在，少数行变化较大。

全部30轮记录的approximate KL均值.0002586、最大.0010214；clip fraction均值.001790、最大.0078125；每轮都完成2epochs。没有证据显示普遍被KL early stop或PPO ratio clip阻断。整体训练entropy均值1.009，代表状态median entropy虽低，抽样只取每轮首个时间步，不能推论整个onpolicy分布普遍饱和。

这些结果支持“小幅策略改动”而非“没有学习”，不能单凭delta/低KL区分小lr、可训练层容量、局部分布、奖励方向。若下一步做单因素幅度实验，可预注册只把lastgraph lr从1e-6提高到3e-6，保持heads lr/原奖励/课程/预算不变，先严格恢复final模型与Adam/RNG，再采全新onpolicy轨迹；这仅测试保守步幅假设，不证明容量不足，也不承诺改善。若改episode调度则不应同时改lr，避免多因素混淆。不得反复看DEV挑lr。

## 已实际归档

`evidence-package-01/ARCHIVE_VERIFIED.json`记录688个去重目标文件、5,442,686,247字节，含冻结来源、全部30checkpoint与rollout、64DEV原JSON/log、原报告及最终独立02证书；每个复制目标重新逐SHA验证，原文件未修改/删除。本报告与后续统计另放补充包，不把只生成计划说成完成复制。
