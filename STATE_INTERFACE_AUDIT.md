# 现有v15观测与模型输入审计

2026-10-14。依据当前实际exporter的NODE_TYPES/EDGE_TYPES和research/battle_features.py，不把设计清单当作已经实现的状态。

| 项目 | v15接口及本轮模型实际使用 | 缺口 |
|---|---|---|
| 行动单位/敌我/是否睡眠 | Unit.IS_ACTIVE、IS_ENEMY、IS_SLEEPING | 需将等待、已行动等语义与规则逐项核对 |
| 兵力和生命 | Unit.VALUE_REL；Player军队相对价值/HP、当步伤害及损失 | 没有逐堆原始数量、当前/总HP和原始兵种ID |
| 攻击、防御、速度 | 引擎提供近战/射击损害关系、行动先后关系、精确合法行动 | 没有原始攻防速数字；当前GNN普通邻接丢弃关系类型/大部分边属性，不能说已完整利用行动次序 |
| 特殊能力/效果 | additional attack、all-around、flying、block retaliation、breath、death cloud、blind、poison、curse等35维属性 | 不能因此宣称已学会或测试全部特殊技能 |
| 位置/双格 | Hex坐标及占据/行动落点关系；合法候选由规则决定 | 候选落点/目标采用聚合，形状、朝向和多目标精确组合表达仍需增强；课程未含龙喷吐/尸巫范围攻击 |
| 回合/行动顺序 | Global.BATTLE_ROUND，Unit.ActsBefore边 | MLP未直接输入完整顺序；GNN未保留边权语义 |
| 障碍/城墙 | Hex passable/stopping/damaging、obstacle、wall、gate、bridge和Global塔标记 | 当前课程没有攻城/随机障碍验收 |
| 英雄/法术 | 当前候选仅WAIT/DEFEND/MOVE/AMOVE/SHOOT | 英雄原始属性、法力、合法施法候选、组合施法均未接入；不能称为魔法AI |
| 终局结算 | terminal_outcome真实战前数量及服务器伤亡，仅用于监督、奖励与评测 | 没有作为Policy输入；复活/召唤的永久结算和冒险层保存仍需专项验证 |

下一版应追加与Unit图行严格对应的原始数量/HP/攻防速、稳定兵种标识、双格footprint与明确行动状态，并保留重要关系的类型/权重。使用已有CStack/CBattleCallback规则查询，不重新猜伤害。扩展schema必须换feature版本、固定ABI并重新采集/训练，不能让旧checkpoint悄悄接收新含义。英雄敌方信息要先核对可见权限，不能为了模型增加隐藏地图或未来信息。

当前初期验收是：普通多兵种战斗中实际训练、合法执行、对照胜率与性能。它不等于主指令列出的全部状态和战术能力已经完成。
