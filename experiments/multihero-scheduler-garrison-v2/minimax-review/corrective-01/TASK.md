你是只读独立审核员，实际运行于DeepSeek Harness的mini / MiniMax-M3.1-Flash。无工具，不执行任何操作。只审查以下实施代理报告；未提供原始日志，你不能声称已核验它们。请直接给中文最终结论，500字以内，别长篇推理，最多3点。

v1工程失败：town tile的hero3并未真驻防，无法资格化scheduler。
v2两臂采用同一fixture同一common setup，只差调度候选的!hero->isGarrisoned()。common setup先cb->swapGarrisonHero，按真实GarrisonHeroSwap包绑定request id/player/town，ACK result成功后同时验证hero3.isGarrisoned、town.garrisonHero==hero3、visitor为空、visitedTown同town、双方owner一致、MP>0，才进入调度。trace记录7种资源、hero owner/garrison/town/army、town upperArmyIDs。两臂编译attestation及accepted源码还原通过。
v2实测（实施代理报告）：两臂真实positive-MP garrison建立且资源/army/stock守恒通过；baseline仍scheduler_selected hero3并发送move，ACK成功但位置不变；filtered成功排除hero3；然而两臂第2回合hero0遇hero2，触发原original-unhandled exchange回调，45秒超时，未满足每hero每turn实际位移闸门。v2整体工程失败保留，不重跑，不放宽门，不宣称资格通过。

下一轮v3已选择：仅改fixture几何，原两组attested候选源码/二进制与其filter单因素不变，不引入close干预；横向全宽水带y9隔离town与mobile，竖水带x9隔离hero0与hero2，竖水带x26隔离敌方；每mobile片区两个远拾取目标分别(4,18)/(4,30)和(18,18)/(18,30)，原生真实garrison仍hero3 positiveMP。独立新fixture/hash及PLAN登记，绝不改写旧v2。每hero每turn实际位移、无超时、无失败move ACK、所有frozen inputs未变的原闸门不放宽；旧臂应由控制被scheduler_selected的负例拒绝，新臂需满足全门。

问题：上述v2失败归因及v3隔离方案能否作为下一轮工程对照？遗漏哪些最必要的可识别性/预注册/审计门？特别区分控制move成功ACK却不位移与scheduler_selected排除的含义，以及v3只能资格化隔离fixture内调度，不能声称完整多英雄战略/互动/训练通过。请给明确结论，不编passed。