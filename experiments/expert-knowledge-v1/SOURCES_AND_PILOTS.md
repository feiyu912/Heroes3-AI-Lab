# 专家来源与试点目录

后续真实执行结果：Hallas等待原理已在固定VCMI中完成8组训练配对、16局正常终局，8组均验证跨轮连续行动窗口。其中4组WAIT与直接行动同损，另4组WAIT损失1条幽灵龙、直接行动损失2条，已生成4条合法首步WAIT候选BC样本。详见 `wait-variant-v2/dataset-audit.json` 和 `wait-train-comparison.json`。幽灵龙老化与伤害随机性尚未做事件级因果隔离；这是来源支持的实验重建与局部配对收益，不能称为高手录像动作提取、普遍最优或已完成学习。8张dev/test地图已冻结，尚未运行。

已整理 11 个来源记录、15 个试点候选。E2 表示实际读到作者的明确文字建议；E1 仅有题名/简介/章节；E0 仅确认频道。没有完成视频观看、字幕提取或高手动作轨迹提取。病例复现及训练结果须见单独执行证据，本目录不自动升级其状态。

最可行的首例是 Richard Hallas 于 2001 年公开发表的 Complete 攻略中的龙反击友伤。定位和17词短引文见 source_case.json；原文为具名实质攻略，不等于认证职业选手比赛录像。阿青仍为优先研究对象，但可访问章节线索不足以重建他的实际操作。

## 来源

- **hallas2001** [Heroes III Complete Strategy Guide — page 5](https://www.insidemacgames.com/historical/features/view.php%3FID%3D64%26Page%3D5.html) — Richard Hallas，2001-08-27，E2_explicit_authored_text_read。Full public text opened successfully
- **aq_dw_collection** [英雄无敌3阿青DW对战骨灰级教学，华山论剑显锋芒（关联青华大学合集索引）](https://www.bilibili.com/video/BV1K4411r7Hu/) — 阿青Hero3，2019-08-23T19:27:40+08:00，E1_metadata_and_chapter_titles_only。Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction.
- **aq_no_magic_elves** [阿青英雄无敌3：禁魔法禁SL，只用大地精灵通关归隐田园，对战思维打单机](https://www.bilibili.com/video/BV1A4411F76m/) — 阿青Hero3，2019-07-07T21:26:48+08:00，E1_metadata_and_chapter_titles_only。Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction.
- **aq_nine_factions** [匠心巨制！最全面的英雄无敌3九族教学，致我们深爱的情怀游戏](https://www.bilibili.com/video/BV1bx4y1Z7wq/) — 阿青Hero3，发布日期未知，E1_metadata_and_chapter_titles_only。Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction.
- **aq_movement** [阿青英雄无敌3：移动力解析，野蛮族演示走位布局](https://www.bilibili.com/video/BV1z4411V7ZY/) — 阿青Hero3，2019-06-15T14:42:32+08:00，E1_metadata_and_chapter_titles_only。Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction.
- **aq_hota_fly** [英雄无敌3阿青入门教程：深渊号角港口族1v7特大双，HOTA随机图飞跳回的终极形态](https://www.bilibili.com/video/BV1z4411U7qu/) — 阿青Hero3，2019-08-15T23:51:58+08:00，E1_metadata_and_description_only。Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction.
- **xiaoz_intro** [〖英雄无敌3〗全b站最详细！！！面向0基础玩家的入门教学](https://www.bilibili.com/video/BV1Aa411D7R7/) — 英雄无敌3狂小Z，2022-07-24T10:06:18+08:00，E1_metadata_and_chapter_titles_only。Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction.
- **coffee_fortress** [英雄无敌3咖啡耐心解说九族系列要塞篇 攻守兼备的霸天种族](https://www.bilibili.com/video/BV1bP411Y7fX/) — 给我一杯咖啡好吗，2023-08-31T09:16:59+08:00，E1_metadata_only。Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction.
- **lexiav_youtube** [Lexiav — official-named YouTube channel](https://www.youtube.com/@Lexiav) — Lexiav，发布日期未知，E0_channel_identified_only。Channel URL opens but tool returns only a small shell; no video metadata/transcript read
- **lexiav_twitch** [Lexiav — Twitch channel](https://www.twitch.tv/lexiav) — Lexiav，发布日期未知，E0_channel_identified_only。Channel opens as empty dynamic shell; no VOD, chapter or transcript extracted
- **gcores_vyi2019** [回忆经典——《英雄无敌3》中的战术细节](https://www.gcores.com/articles/109112) — v翼，2019-05-09，E2_explicit_authored_text_read。Full public text opened successfully

## 15个候选

|编号|候选|证据及当前范围|
|---|---|---|
|P01|诱导龙反击误伤友军|explicit_text_claim_not_trajectory；v15_battle_no_active_magic|
|P02|己方龙站位防反击喷吐陷阱|explicit_text_claim_not_trajectory；v15_battle_no_active_magic|
|P03|护射手与片伤防守的取舍|explicit_text_claim_not_trajectory；v15_battle_no_active_magic|
|P04|最快兵等待形成跨轮连续行动|explicit_text_claim_not_trajectory；v15_battle_no_active_magic|
|P05|被贴射手等待友军解围后射击|explicit_text_claim_not_trajectory；v15_battle_no_active_magic|
|P06|射手分散避免一兵同时封两队|explicit_text_claim_not_trajectory；v15_battle_no_active_magic|
|P07|高速兵风筝保持威胁距离|explicit_text_claim_not_trajectory；v15_battle_no_active_magic|
|P08|片伤射手价值判断导致发呆|chapter_title_lead_only；v15_legacy_ai_exploit_candidate|
|P09|无失明站位价值绑定形成假控制|chapter_title_lead_only；v15_legacy_ai_exploit_candidate|
|P10|禁魔法大地精灵站位与游击|chapter_title_lead_only；v15_battle_candidate_exact_tactic_unknown|
|P11|狂小Z基础兵种机制交叉核验|chapter_title_lead_only；v15_battle_candidate_exact_tactic_unknown|
|P12|咖啡要塞防守操作候选|metadata_lead_only；v15_battle_candidate_exact_tactic_unknown|
|P13|Lexiav职业实战的战术取舍|channel_lead_only；future_evidence_collection|
|P14|兵链、支点与一兵多用|mixed_text_mechanism_and_video_topic_only；strategy_archive_deferred|
|P15|飞跳回与技能经济评价|metadata_lead_only；strategy_and_active_magic_deferred|

## 筛选与限制

按可定位原始证据、规则可验证性、当前接口适用性筛选；不以播放量决定真伪。标题线索不生成专家动作。没有字幕/存档的内容保留未知，具体兵力和坐标由实验创建时必须标明实验重建。

B站直接页面访问出现 HTTP 412/读取失败，因此只使用公开搜索索引显示的原发布元数据，没有绕过限制。YouTube/Twitch只返回频道外壳，没有获取VOD或字幕。没有下载或再分发视频。B站页面注明未经授权禁止转载；来源许可未知，不声称拥有视频/完整字幕训练授权。

Complete、SoD、HotA及VCMI需分别记录版本。龙喷吐方向与双格占位必须由固定版本真实执行核验；旧AI发呆漏洞不代表VCMI BattleAI也有。英雄主动施法、飞跳回、兵链、技能和经济暂归后续/战略档案。

要进一步做阿青、Lexiav等真实操作提取，需要可合法读取的字幕/讲解文本、明确时间定位或获许可的存档/回放。任何输入仍需确认版本、可观测状态和动作合法性；不依赖视频坐标猜测。
