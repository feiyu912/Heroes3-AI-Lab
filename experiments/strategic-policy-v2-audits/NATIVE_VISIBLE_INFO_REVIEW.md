# 真实 v3 可见威胁/补给观测复核（2026-10-18）

已完成的 `v3-visible-info-smoke-01` 是一局对 NK 的真实败局：224个请求/动作正常、原生完整终局。只读 CPU 复核通过，不认证战略收益，没有启动新游戏、CUDA context 或 optimizer，也没有修改供给试点冻结的任何 v2.py。

原始报告：`native-v3-03/AUDIT.json`。agent目录 `/root/heroes3-ai-lab/workers/strategy-agent-runs/v3-visible-info-smoke-01-sk2ntgdz`；native目录 `/root/heroes3-ai-lab/workers/adv-runs/v3-visible-info-smoke-01-2026101923-587vye4m`。报告保存原 smoke/native plan 的完整输入SHA和审计脚本副本，结论针对该完成时快照；允许后续在保留历史变体后正常研发，不要求未来工作树永远保持旧SHA。

## 强敌观测未被攻击筛选抹掉

224份严格v3观测中123份含当前可见敌英雄，累计319个敌英雄观测条目；98份含粗略兵力大于自军的敌英雄。原生214条 `kind0/status=strength_filter` 敌英雄事件全部能在相同day/hero/from请求的visible_threats找到相同位置、相同粗略强度，覆盖98个请求上下文。该过滤检查的 tile_visible 均为1。

源快照确认：先检查visitable位置可见，再通过允许的 `getHeroInfo(obj,enemy,hero)` 获得粗略信息，然后加入visibleThreats，最后才过滤攻击候选。中立军队的 `neutral_strength_filter` 与敌城kind1过滤未冒称敌英雄信息；getHeroInfo失败的对象也未擅自加入。该证据表明本局的强敌不会因为无法直接攻击而从新观测消失，不等于全地图隐藏敌军都可见。

## 自城位置和驻军重算

before_move记录有town id和精确兵组，但没有town坐标。位置因此从本局实际 `.vmap` 的objects.json对象序号与template中A访问信息格独立重建，然后与每个请求的own_towns比较，不能声称“原始trace直接含城坐标”。本局有243个自城条目快照，位置和顺序全部一致。

兵力不从网上记忆值或模型value反推：读取实际游戏Data/H3bitmap.lod内CRTRAITS.TXT，提取AI Value列；结合实际castle/rampart config的core索引，按原生ArmyDescriptor详细模式 `sum(AIValue×count)` 重算。实际涉及ID0枪兵80、ID2弓箭手126、ID14半人马100。243个驻军值与对应before_move兵组全部相等；英雄own_army_value同样全部相等。例如首请求自城14枪兵+9弓箭手＝2254，英雄20枪兵+10弓箭手＝2860。

数据LOD、抽取文本、使用配置和源码的SHA均在报告保留。复核器对未审计到的其他生物索引会失败，不用未经核对的通用表替代实际资产。

## 新模型消费与迁移

224份请求严格schema、26/23维特征全部有限，范围约[-0.888889,1.513925]，169份为单候选。每份请求字节SHA、返回动作SHA与broker trace一致；对应native选中目标/next一致。使用同冻结新模型在CPU按完整原始请求重算，所有224个argmax动作一致，记录value误差为0。新模型与父v1模型在这些真实请求上logit/value最大差1.19e-7，符合零新增输入权重迁移的预期。

迁移权重SHA为 `804aab1aeb3fcc7e685891b469abe1efaf309399619f4d47771382f3d70571d0`，父SHA为 `f524796161915cb43ae9e228f13dd72c195df016ce5d2c25dab7d8a7d2aeb7cc`，lineage完整指向更早pilot02 parent。新增协议optimizer=None、step=0，没有把旧训练冒称新特征学习。

broker源快照确实对完整v3请求调用新encoder；不过原始broker没有记录编码后tensor的hash。本次报告的224个feature SHA是独立重算，不能冒称运行时已记录。新列权重全0意味着动作/value一致本身也无法证明策略已经利用新信息；本轮只证明接口提供信息、数值可编码、消费链条相符。

首两次审计尝试分别遇到原生配置含注释不符合标准JSON、及重招英雄带ID14半人马超出最初只审计Castle索引的范围；已改为明确检查配置override并补实际Rampart索引/CRTRAITS来源，保留空失败目录，最终第三次通过。没有为通过而改原始请求或游戏资产。

对NK依然是败局。新增威胁/驻军信息、完整边界恢复与机制改进，均不能代替新冻结候选对同条件baseline的独立配对评估。
