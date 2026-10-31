# 2026-10-24 本轮继续状态（未完成完整目标）

## 最新状态：战略课程配对学习已启动

战斗恢复对照已完成（session3804正常0退出），两臂最终68/累计8704实际Adam，
各新增1024、4096准入+4096零损失后缀。96独立DEV全部正常，2347完整CPU决策
重放、4892原始哈希通过。父60/control68/candidate68的BattleAI均15/16；
MMAI分别14/16、13/16、13/16。candidate对control一正一负，无净胜局收益；
不晋升模型，不声称95%，finaltest未动。完整68模型/证书交付：
terminal-credit-delivery-01/{AUDIT.json,REPORT.md,control-update-68.pt,candidate-update-68.pt}。
原始资源失败仍为false；恢复期间min available6000.8MiB/maxswap39.5MiB。

TRAIN校准及独立12原始+11058CPU proposal已全部完成，选择x4，
但成功仅在矿区2格，发展图仍败。700544556字节/27939普通文件归档完整。
此前缓存原型现仅在新的课程学习包装器正式使用：长局完整报告等于原无缓存审计，
原审计器源码和全部闸门未改。旧epoch不改。

新实际研究：../strategic-active-opponent-learning-20261024，独立policy-v4目录，
两组同1510149e初始模型，各自新Adam/RNG。control x1；curriculum仅NK x4。
各8完整新鲜随机on-policy TRAIN，seed2026104400..4407，固定原4epoch PPO、
LR3e-4、等回合权重/终局±1；1次更新，各自实际Adam不强行相等。
地图统一私有规范源文件名，配对采样seed消除地图别名干扰；分歧后不是逐动作配对。
全部更新+实际CUDA恢复/12负例通过后，共享初始化+两模型，原未增强DEV24局，
2026104600..4607；无中途择模，无校准轨迹训练准入，无finaltest。
16格prepare-only、8错误配置、CPU codec、缓存完整等价均通过。
17保护文件精确且无活动native/GPU；706项source freeze：
c19ac372d22b3156172f02a65f8ad1ef4dc635a15737775eb8cf98c3b31467f7。

实际运行/root/heroes3-ai-lab/evaluations/strategic-active-learning-native-01，
session83321。运行状态须用watch_active_learning.py复核，不得编辑新冻结包任一源。
新包装器所有native继承真实GPU→pool锁，退出清理后放锁；每阶段前后2GiB/256MiB
资源门。独立完整40原始+24CPU重放脚本review_active_learning.py已准备，
只能在学习器全部退出后执行，避免重CPU诊断与学习器争内存。

本次另有一次真实dsh MiniMax有限方法审核，session-d73a6a32-b33b-483f-ac8b-38ae5b9ed78d，
mini/MiniMax-M3.1-Flash，input707/output597，4096/low/零工具；完整证据在新研究
minimax-method-review。仅读方案报告，无原始审核资格。采纳记录真实长度/Adam差异、
分布处理包限度和共同seed局限。其第三臂建议不自动变成必要门，finaltest字样不是开封授权。

以下为保留的较早工作快照；其中“当前运行中/未DEV”等已经由以上最新结论替代。

---


完整目标和历史原始索引仍见根目录 NEW_CHAT_HANDOFF_20261023.md 及本目录
GOAL_STATUS.md；用户已明确继续，并允许把部分任务交给 dsh 中的 MiniMax。
本文件是持续工作快照，任何运行中状态须再次核验进程和资源锁。
平台get_goal仍显示旧goal为blocked；create_goal恢复尝试被拒，错误为已有未完成
goal，必须先complete。完整目标实际未完成，绝不可为绕过接口把它标complete。
当前工作照用户继续授权正常执行；工具没有恢复状态接口。

实际 dsh 委派已完成，mini/MiniMax-M3.1-Flash：
`../multihero-scheduler-garrison-v2/minimax-review/RESULT.json`。
首轮长源码审核 max-tokens 无 final，保留为失败；第二轮4096/low/零工具成功，
只审实施者报告的v2失败与v3计划，未独立审核v4原始结果。

调度v4有限工程资格已完成：
`../multihero-scheduler-garrison-v4/REPORT.md`、independent-review-02/AUDIT.json。
baseline只因选择真实正移动力驻防英雄3被拒；filtered全部严格闸门通过。
两组每名移动英雄11条成功请求（turn1=10/turn2=1），每回合真实位移；
原生无pending边界停止。五类坏证据检查、17冻结哈希、源码唯一过滤差异通过。
普通原生日志另匹配2个真实GarrisonHeroSwap与44个MoveHero请求ID。
原始v1失败、v2交换/转兵证据不变。v2/v3新失败均保留。
build-evidence-04保存23文件/75,229,845字节，逐项等于WSL原件。
此资格不等于一般多英雄策略/神经调度/整体取胜；没有据此启动战略PPO。

招募四臂DEV已完成：32局全部四臂各4/8，独立32原始审计和12787完整CPU
proposal复算通过。见 independent-evidence-01/priorzero-dev-actual-01/AUDIT.json。
手工-4改0不等于学习；没有独立收益，不升级模型。

下一因素采用TRAIN主动对手难度校准，12格×1/×2/×4，只改己方实际初始英雄
兵量，不改敌军/经济/地图其他内容。新隔离生命周期修正包：
`../strategic-active-opponent-curriculum-v2-20261023`；使用同schema6 capsule02、
固定zero初始化1510149e…e1c62a1、CPU argmax。12格严格地图再推导与collector
prepare-only通过，无GPU/原生；之后实际运行已启动：
`/root/heroes3-ai-lab/evaluations/strategic-active-calibration-v2-native-01`。
登记必须12正常有效终局，选择首个×2/×4达到≥2/4，绝不追加网格/种子。
已全部12格完成：原始量0/4、双倍1/4、四倍2/4，按登记选择4倍。
第三格四倍为111天/2880决策长局，完整原始审计正常消耗较久，不能跳过。
独立审计跟进在 independent-evidence-01/calibration-actual-01，完成原始审计
和完整CPU proposal重放；12格/11058 proposal全部通过，AUDIT.json为最终证书。
INITIAL_STATE_AUDIT.json另核验12格真实初始军队/catalog/私有地图SHA全部正确。
运行session72640/25802均已正常结束。完整普通文件归档在calibration-delivery-01，
session81248已完成：27939文件/700544556字节全部原件哈希相等，105296KiB内存峰值，
无swap、仅顺序IO；不加载NN分析模型。
parser-cache-equivalence-01对2880决策长局验证完全相同审核结果，4529次cache命中、
4次解析、12.265秒；原审核器/运行进程未改，此原型尚未进入生产资格路径。

战斗终局延伸首轮：
`/root/heroes3-ai-lab/evaluations/battle-terminal-credit-01`。
原生资格2048转移/0新Adam通过，16槽均有真实终局延伸，独立目标审计通过。
control/candidate micro61/62各256实际Adam、各1024准入+1024后缀，通过完整审计。
跨臂61后model/Adam/四RNG全同，全部第一阶段原始观察/动作/后缀全同。
62的253准入行目标变化，最大0.9555967；182参数张量改变，L2差0.0313003。
证据 terminal-credit-independent-01/{COMMON_FIRST_UPDATE,MICRO_TARGET_COMPARISON}.json。

首轮control phase1完成63/64并保存完整64后，post_update_resource资源检查失败，
原始RESULT保持false；不得改写为通过。64前的63记录available7142.63MiB、
swap181.57MiB，具体失败时指标未保存，不能凭后来状态虚构。
大型CPU跨臂诊断曾与GPU/原生学习重叠，可能贡献资源压力，但未证明因果。
所有worker/learner已清理，随后校准能实际取得GPU→pool锁；没有96DEV。

独立恢复审计已通过 control63/64完整模型/命名Adam/四RNG/counters、phase1的
全部256原生journal、reward/targets/suffix/privateRNG，证明完整64学习器边界：
terminal-credit-recovery-review-01/AUDIT.json。原始资源门仍false。
可从control64恢复65，candidate62恢复63；绝不重跑control phase1、重置Adam、
重播种或多做优化。原生phase本来即fresh，无恢复in-flight游戏。

新的恢复控制器（已经CPU plan-only/语法核验，已开始execute）：
`../battle-terminal-credit-recovery-20261023/{PLAN.md,run.py}`。
它复用原冻结train.py/audit.py；只调整调度接续、轻量内存遥测及禁止大型CPU
分析与学习器重叠。资源阈值、16worker、算法、seed、预算全部不变。
校准与独立复核均结束后已实际执行，session3804：

```
wsl -d Ubuntu-22.04 -- python3 /mnt/g/Heroes3-AI-Lab/experiments/battle-terminal-credit-recovery-20261023/run.py --out /root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-01 --execute --evaluate
```

顺序candidate phase1补到8192，然后control/candidate phase2/3同链到8704/global68。
当前/root/heroes3-ai-lab/evaluations/battle-terminal-credit-recovery-01为活动封存运行，
绝不可修改其run.py/PLAN或旧learner/audit/freeze；只可轻量监测。
watch_bounded.py --run该目录可读阶段/内存，不加载Torch。
恢复candidate phase1已完成且独立审计通过，两臂均达8192实际Adam；最低可用
内存6321MiB/swap0。当前control phase2进行中，未有DEV。
仅全部严格原始/预算门通过后，原登记96DEV一次（新7600种子epoch）和完整NN重放。
若再失败保留停止、诊断，不重播。报告必须注明恢复比较及原不对称资源停止，
不可写成原始全程协议通过。原始冻结包任何文件都不能改，尤其train/learner/audit。

始终GPU锁→pool锁、非阻塞、单GPU学习器，锁文件不删除。无24worker认证、
无final-test、无伪教师或视频理解、无模型升级。用户授权持续实施，无需重复确认。
