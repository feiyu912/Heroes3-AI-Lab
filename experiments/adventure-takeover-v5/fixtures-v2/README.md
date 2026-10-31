# 战略发展地图组 v2：六图，先划分再执行

本组独立于旧三个开发地图。生成器不启动游戏；所有 `engine_load_verified=false` 均表示等待主窗口真实验收，不能把 ZIP/JSON 静态检查说成 VCMI 已加载。

| 资源名（均加 `Maps/adv/`） | 预划分 | 双侧野外内容 |
|---|---|---|
| `takeover-v2-train-01-mines` | train | 各一金币/木材/矿石资源堆、无主伐木场/矿石坑；最小加载与占矿/拾取验证 |
| `takeover-v2-train-02-development` | train | 上述内容 + 各一守卫金矿、一中立可占城、一队野兵 |
| `takeover-v2-dev-01-river` | dev | 同类发展目标，中央水墙改变路线，资源位置和兵数变化 |
| `takeover-v2-dev-02-reserves` | dev | 同类目标，资源位置和兵数变化 |
| `takeover-v2-test-01-river` | test | 预先冻结的中央水墙图；不得用于训练/专家选择 |
| `takeover-v2-test-02-reserves` | test | 预先冻结的开放图；不得用于训练/专家选择 |

六图全部 36×36 单层，初始双方各一个 Castle 城镇与一个核心骑士，20 枪兵 + 10 弓箭手。城镇具备 fort/villageHall/townHall/tavern/一级及二级兵营。中立城只有 villageHall/一级兵营及适度枪兵守军，拥有后提供正常收入/招募机会。金矿和野兵守军为 6–12 枪兵，中立城为其再加 4；不是声称已验证难度适中或一定值得打，真实损失和战略收益待实验。

地图无需主动英雄魔法、作弊资源或特殊胜负。继续使用引擎正常战胜所有对手与无城天数失败条件。没有公开全部地图的额外对象、没有初始视野揭示、没有传送、没有回合脚本赠送、没有直接给 AI 隐藏敌情。具体策略必须只使用合法可见观测，不得根据生成器的全地图坐标选目标。

## 字段和模板是如何核实的

- `config/objects/moddables.json` 明确注册 resource:wood/ore/gold 及矿山 sawmill/orePit/goldMine；资源图形文件名、资源模板 `mask=["VA"]`、访问方向均来自此实际隔离源码。
- `lib/mapObjects/CGResource.cpp::serializeJsonOptions` 明确读取 `amount`，不是未经验证的 `resources` 选项；使用确定的 core 资源类型，金币 `amount` 为实际金币数，不走 randomResource 换型倍乘。
- `lib/mapObjects/MiscObjects.cpp::CGMine::serializeJsonOptions` 读取 owner，继承 CArmedInstance 的 `army`；常规金矿无额外默认守军，明确的地图守军保留。普通矿山产量由原生构造器配置决定，未发明地图中的 `income` 字段。
- 中立城复用已跑通的 Castle 模板；owner=null，buildings 与 army 使用 CGTownInstance 的实际序列化入口。
- 野怪使用 CGCreature 的 `amount`、`character="savage"`、`noGrowing=true`、`neverFlees=true`、`upgradedStackPresence="never"`；这些键和枚举均逐项在实际源码核实。
- 矿山与枪兵模板直接读取本机合法游戏资源 `H3bitmap.lod` 的 Objects.txt，并读取 `H3sprite.lod` 对应 `.msk` 尺寸，照隔离 `ObjectTemplate::readTxt/readMsk/writeJson` 的底部锚点、坐标反向索引转换成 JSON。没有猜矿山 DEF 名称或碰撞范围。
- `core-template-audit.json` 保留 Objects.txt SHA、少量模板元数据和来源路径。没有复制/再分发原始图像、音频或完整游戏档案。

## 可复核产物

`extract_core_templates.py` 读取本机核心模板；`generate_development_maps.py` 定义六图全部配方及 train/dev/test 划分，先生成 `--minimal-only` 最小图，再生成全组。

`sources/<地图名>/` 保留三个源 JSON；`maps/` 保留确定性 ZIP；`suite-audit.json` 保留各图 SHA、源代码字段定义文件 SHA、配方、对象列表与静态检查。安装路径为独立新文件 `/root/heroes3-ai-lab/data/vcmi/Maps/adv/takeover-v2-*.vmap`，拒绝覆盖不同内容的同名地图。

静态检查包含：ZIP 回读一致、模板阻挡/访问格不越界、不重叠、不在水上；四邻接粗粒度可达所有访问格；新增成对目标的类型、资源/军队价值配置相同且访问坐标关于 x=17.5 镜像；地形镜像；双方起始军队与城镇建筑相同。静态 BFS 没有计算原生路径层、迷雾、斜走、警戒或查询规则。

## 公平性及测试边界

- 引擎正常难度决定起始资源，没有给某方额外资源。实际加载仍需记录双方真实初始资源与军队；配置相称不能代替实测。
- 英雄为 Christian 与 Sorsha，专长不同；源模板与城镇图形保持原生朝向，因此相同的访问坐标镜像不保证每条道路代价绝对相等。需要交换双方策略/出生位置检验角色影响，不能将图组当作已证明对称的胜率测试。
- 旧三图与新六图及其配方均不改写已跑结果。新 test 两图只能先做规则/加载完整性检验，不能读取胜负后再选模型、重配地图并继续叫独立测试。如果后续修地图内容，必须另建版本并重新冻结划分。
- 六图很少，固定地形和兵种覆盖有限；先用于真实战略数据管线与开发/独立验收起点，不能据此宣称超大图 1v7、长期规划或通用战略能力已完成。
