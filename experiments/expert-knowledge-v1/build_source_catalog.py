"""Curated public metadata and concise source claims; no media downloader."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATE = "2026-10-15"

def source(id, title, author, url, published, version, kind, topics, evidence, access, locator=None):
    return dict(id=id, title=title, author=author, url=url, published_at=published,
                game_version=version, material_type=kind, topics=topics,
                evidence_level=evidence, access_observed=access, content_locator=locator,
                accessed_at=DATE, video_watched=False, transcript_extracted=False,
                structured_human_trajectory_available=False,
                reliability="Source existence and stated topic are distinct from tactical correctness; experimental verification required",
                rights={"reuse_license":"unknown", "media_downloaded":False,
                        "allowed_by_this_pipeline":"links, bibliographic metadata, concise original paraphrase; no full transcript or video redistribution"})

BILI = "Search index exposed original publication metadata/chapters; direct page fetch returned HTTP 412 or internal fetch error. No attempt to bypass; no playback, subtitle or state extraction."
sources = [
source("hallas2001", "Heroes III Complete Strategy Guide — page 5", "Richard Hallas",
 "https://www.insidemacgames.com/historical/features/view.php%3FID%3D64%26Page%3D5.html", "2001-08-27", "Complete; exact executable build unknown", "original_text_tutorial",
 ["dragon_retaliation_friendly_fire", "shooter_screening", "waiting", "formation"], "E2_explicit_authored_text_read", "Full public text opened successfully", "General combat tips; Make retaliation count; Range-attacking troops; Waiting to attack"),
source("aq_dw_collection", "英雄无敌3阿青DW对战骨灰级教学，华山论剑显锋芒（关联青华大学合集索引）", "阿青Hero3",
 "https://www.bilibili.com/video/BV1K4411r7Hu/", "2019-08-23T19:27:40+08:00", "DW manual-combat rules; exact game build unknown", "original_video_metadata_and_collection_index",
 ["legacy_ai_valuation", "dragon_breath", "battle_value", "BT_problem_solving", "army_chaining"], "E1_metadata_and_chapter_titles_only", BILI,
 {"important_distinction":"following chapter names belong to linked collection items, not necessarily this video's own parts; direct item IDs unresolved", "chapter_titles":["利用AI的价值判断导致敌方片伤远程的发呆", "无失明魔法，利用站位价值绑定电脑走位，形成假控制", "巧用龙息，误伤的魅力", "英雄无敌3〖BT图〗战场机制研究，致每一位热爱H3的玩家"], "timestamps":None}),
source("aq_no_magic_elves", "阿青英雄无敌3：禁魔法禁SL，只用大地精灵通关归隐田园，对战思维打单机", "阿青Hero3",
 "https://www.bilibili.com/video/BV1A4411F76m/", "2019-07-07T21:26:48+08:00", "exact version unknown; description forbids magic and save/loading", "original_video_metadata",
 ["ranged_micro", "positioning", "attrition"], "E1_metadata_and_chapter_titles_only", BILI,
 {"parts":["P3：站位威慑", "P5：以弱胜强", "P6：游击消耗"], "timestamps":None}),
source("aq_nine_factions", "匠心巨制！最全面的英雄无敌3九族教学，致我们深爱的情怀游戏", "阿青Hero3",
 "https://www.bilibili.com/video/BV1bx4y1Z7wq/", None, "mixed rules possible; exact version unknown", "original_video_metadata_and_collection_index",
 ["nine_factions", "economy", "development"], "E1_metadata_and_chapter_titles_only", BILI, "九族手册合集；发布时间未取得可靠完整字段"),
source("aq_movement", "阿青英雄无敌3：移动力解析，野蛮族演示走位布局", "阿青Hero3",
 "https://www.bilibili.com/video/BV1z4411V7ZY/", "2019-06-15T14:42:32+08:00", "exact version unknown", "original_video_metadata_and_collection_index",
 ["adventure_movement", "army_chaining", "terrain"], "E1_metadata_and_chapter_titles_only", BILI, "青华大学相关课程；章节名和时长可见，但非已确认技巧时间戳"),
source("aq_hota_fly", "英雄无敌3阿青入门教程：深渊号角港口族1v7特大双，HOTA随机图飞跳回的终极形态", "阿青Hero3",
 "https://www.bilibili.com/video/BV1z4411U7qu/", "2019-08-15T23:51:58+08:00", "HotA; exact version unknown", "original_video_metadata_and_description",
 ["adventure_fly_dimension_door_town_portal", "1v7"], "E1_metadata_and_description_only", BILI),
source("xiaoz_intro", "〖英雄无敌3〗全b站最详细！！！面向0基础玩家的入门教学", "英雄无敌3狂小Z",
 "https://www.bilibili.com/video/BV1Aa411D7R7/", "2022-07-24T10:06:18+08:00", "includes Cove; exact version unknown", "original_video_metadata_and_chapter_index",
 ["factions", "basic_rules", "magic"], "E1_metadata_and_chapter_titles_only", BILI, "15-part index available; no verified move-level tactical segment"),
source("coffee_fortress", "英雄无敌3咖啡耐心解说九族系列要塞篇 攻守兼备的霸天种族", "给我一杯咖啡好吗",
 "https://www.bilibili.com/video/BV1bP411Y7fX/", "2023-08-31T09:16:59+08:00", "exact version unknown", "original_video_metadata",
 ["fortress", "defense"], "E1_metadata_only", BILI, "耐心要塞P1/P2；未取得字幕或具体战术定位"),
source("lexiav_youtube", "Lexiav — official-named YouTube channel", "Lexiav",
 "https://www.youtube.com/@Lexiav", None, "HotA often attributed by community; individual video rules must be checked", "creator_channel",
 ["competitive_play", "duel"], "E0_channel_identified_only", "Channel URL opens but tool returns only a small shell; no video metadata/transcript read", None),
source("lexiav_twitch", "Lexiav — Twitch channel", "Lexiav",
 "https://www.twitch.tv/lexiav", None, None, "creator_channel",
 ["competitive_play"], "E0_channel_identified_only", "Channel opens as empty dynamic shell; no VOD, chapter or transcript extracted", None),
source("gcores_vyi2019", "回忆经典——《英雄无敌3》中的战术细节", "v翼",
 "https://www.gcores.com/articles/109112", "2019-05-09", "H3 with expansion discussion; exact executable unknown", "original_authored_community_article",
 ["speed_initiative", "waiting_double_action", "kiting", "army_chaining", "adventure_magic"], "E2_explicit_authored_text_read", "Full public text opened successfully", "（3）控制法术，速度和等待段；（1）移动力，兵链段"),
]

def pilot(id, name, source_ids, locator, evidence, fit, offense, defense, test, failures, priority=2):
    return dict(id=id, tactic_name=name, source_ids=source_ids, evidence_location=locator,
                extraction_status=evidence, scope=fit, priority=priority,
                tactic_goal=offense, key_mechanics=[], preconditions=[], operation_order=[],
                success_reason=None, failure_conditions=failures,
                offense=offense, defense=defense, opponent_response=defense,
                proposed_validation=test, game_version="inherit source; VCMI equivalence unverified",
                human_state_fields_unknown=["coordinates", "counts", "hero skills", "seed", "exact build"],
                video_time_start_seconds=None, video_time_end_seconds=None,
                extraction_confidence="high_text_claim" if evidence.startswith("explicit") else "topic_only_no_action_confidence",
                reconstruction_status="not_executed", learning_status="not_used_for_training",
                benchmark_status="not_run", generality="to_be_determined",
                split_policy="group by tactical template and unit-family; independent test fixtures and seeds held out before labeling/training",
                bc_gate="Only engine-legal demonstrated actions with measured advantage; source titles never become labels",
                ppo_gate="Only valid training split scenarios; preserve old baselines; evaluate both offense and defense plus ordinary battles")

pilots = [
pilot("P01", "诱导龙反击误伤友军", ["hallas2001", "aq_dw_collection"], "Hallas: Make retaliation count; 阿青关联章节仅为线索", "explicit_text_claim_not_trajectory", "v15_battle_no_active_magic", "用进攻方向诱发有利的敌方喷吐友伤", "移开后排、消耗反击或拒绝该站位", "同种子比较诱导与错位对照，核对反击事件、受伤阵营与战损价值", ["反击已耗尽", "龙被秒杀", "方向或双格几何错误"], 1),
pilot("P02", "己方龙站位防反击喷吐陷阱", ["hallas2001"], "Make retaliation count / Conversely paragraph", "explicit_text_claim_not_trajectory", "v15_battle_no_active_magic", "保持己方部队不落入己方龙的反击延长线", "攻击者改换角度创造新的诱导线", "枚举合法进攻方向，比较重排前后己方友伤和存活", ["单看中心坐标忽略双格占位", "威胁由下一步新产生"], 1),
pilot("P03", "护射手与片伤防守的取舍", ["hallas2001"], "Range-attacking troops", "explicit_text_claim_not_trajectory", "v15_battle_no_active_magic", "阻挡近战接触同时避免群体暴露", "范围伤害对手选择更有利目标或方向", "同等兵力对比紧贴屏障与合法分散屏障，记录射击机会与群体战损", ["射手仍被贴身", "屏障本身造成更高片伤"], 1),
pilot("P04", "最快兵等待形成跨轮连续行动", ["hallas2001", "gcores_vyi2019"], "Waiting to attack；机核（3）速度段", "explicit_text_claim_not_trajectory", "v15_battle_no_active_magic", "本轮后手接下轮先手形成行动窗口", "对手保留行动、拉开距离或改变速度序", "记录两次行动之间敌方是否获行动及收益；与直接进攻同种子比较", ["并非场上最快", "同速攻守规则", "士气改变顺序", "等待让射手免费输出"], 1),
pilot("P05", "被贴射手等待友军解围后射击", ["hallas2001"], "Waiting to attack / When it's the range-attackers' turn", "explicit_text_claim_not_trajectory", "v15_battle_no_active_magic", "延后射手行动争取恢复合法射击", "贴身单位存活或再次贴身", "必须实测WAIT后解围及SHOOT合法性，比较伤害和射手损失", ["友军无法清掉封锁", "后续敌方仍能贴身"], 1),
pilot("P06", "射手分散避免一兵同时封两队", ["hallas2001"], "Troop formation / final sentence", "explicit_text_claim_not_trajectory", "v15_battle_no_active_magic", "减少一个敌方站位同时封锁多个射手", "飞兵选择仍能封锁的共同邻接格", "枚举可达格及射手被封数量；对照两种阵型", ["忽略双格与飞行可达性", "分散降低集火"], 2),
pilot("P07", "高速兵风筝保持威胁距离", ["gcores_vyi2019"], "（3）控制法术中的速度与主动性段", "explicit_text_claim_not_trajectory", "v15_battle_no_active_magic", "用速度差减少被攻击机会", "对手截路、等待或守住射手", "合法可达集与攻击威胁核验，多轮对照；禁止把拖到截断当成功", ["棋盘边界", "速度优势不足", "回合上限"], 2),
pilot("P08", "片伤射手价值判断导致发呆", ["aq_dw_collection"], "关联合集章节：利用AI的价值判断导致敌方片伤远程的发呆；确切视频ID和时间未知", "chapter_title_lead_only", "v15_legacy_ai_exploit_candidate", "研究特定旧AI价值判断漏洞", "新AI识别可获利合法射击或改变站位", "先取得授权可核验文字/存档，再对Complete和VCMI分别测试，不能从标题推导成立", ["VCMI不复刻旧AI估值", "缺实际局面", "当前对手并非旧AI"], 2),
pilot("P09", "无失明站位价值绑定形成假控制", ["aq_dw_collection"], "关联合集章节：无失明魔法，利用站位价值绑定电脑走位，形成假控制", "chapter_title_lead_only", "v15_legacy_ai_exploit_candidate", "发现布局是否能限制特定AI选择", "拒绝价值诱饵并选择总体收益更高路线", "取得可核验局面后比较多AI和随机变体，标记仅对哪个实现有效", ["机制未识别", "基线无此缺陷"], 2),
pilot("P10", "禁魔法大地精灵站位与游击", ["aq_no_magic_elves"], "P3站位威慑/P6游击消耗；具体事件时间未知", "chapter_title_lead_only", "v15_battle_candidate_exact_tactic_unknown", "筛选无需英雄魔法的射手操作", "侧翼包抄或阻断撤退", "只将后续取得明确状态证据的片段重建；不能把整个通关题名当样本", ["所述游击可能属于大地图", "状态未知"], 2),
pilot("P11", "狂小Z基础兵种机制交叉核验", ["xiaoz_intro"], "分族章节，尚无具体战斗定位", "chapter_title_lead_only", "v15_battle_candidate_exact_tactic_unknown", "寻找第二作者对试点机制的独立讲解", "用机制例外作为反例测试", "取得明确片段/文本后核对游戏规则，不按播放量评级", ["教程话题并非具体操作", "版本不同"], 3),
pilot("P12", "咖啡要塞防守操作候选", ["coffee_fortress"], "耐心要塞P1/P2；尚无战术定位", "metadata_lead_only", "v15_battle_candidate_exact_tactic_unknown", "寻找要塞兵种防守与反制实例", "高速侧切、远程逼迫其离位", "先确认原文和动作条件，再决定是否形成案例", ["仅标题可见", "不能确认是否依赖施法"], 3),
pilot("P13", "Lexiav职业实战的战术取舍", ["lexiav_youtube", "lexiav_twitch"], "创作者频道；具体VOD/时间位置未取得", "channel_lead_only", "future_evidence_collection", "寻找真实竞技对手下的操作和反制", "同时记录对手回应，避免只学胜方动作", "需要可访问原视频字幕或许可结构轨迹；目前不产生BC标签", ["频道动态页面无内容", "职业身份与具体规则未验证"], 3),
pilot("P14", "兵链、支点与一兵多用", ["aq_dw_collection", "aq_movement", "gcores_vyi2019"], "兵链研究关联合集/移动力教程；机核（1）移动力", "mixed_text_mechanism_and_video_topic_only", "strategy_archive_deferred", "减少大地图运兵与移动损耗", "切断接力节点或威胁副将", "等待大地图状态、物品转移与移动动作接口；禁止塞入战斗BC", ["v15无大地图接口"], 3),
pilot("P15", "飞跳回与技能经济评价", ["aq_hota_fly", "aq_nine_factions"], "原视频标题/合集信息；具体细节未提取", "metadata_lead_only", "strategy_and_active_magic_deferred", "归档战略效率与资源决策", "预测落点、控制城镇与补给节点", "独立战略知识库；待地图与英雄施法接口和版本核验", ["v15无主动英雄施法", "大地图未接入", "HotA与Complete差异"], 3),
]

registry = {"schema_version":1, "created_at":DATE, "scope":"public-source pilot; not completed video understanding", "evidence_scale":{"E0":"channel identified", "E1":"metadata/title/description/chapters only", "E2":"explicit authored text actually read", "E3":"human state/action trace verified", "E4":"pinned VCMI replication with controls"}, "sources":sources,
 "selection_criteria":["Original creator publication preferred", "Exact rule/version and source locator required before labels", "Independent authors and mechanism checks, no popularity-based correctness", "Current non-active-magic battle mechanics first", "Unknown state remains null", "No source title or model speculation as demonstration", "No bypass of access restrictions or unauthorized bulk media redistribution"],
 "rejected_or_unpromoted":[{"url":"https://heroesmightandmagic3.wiki/guides/combat/", "reason":"Search result describes an unverified 2026 H3 Remake; wrong/unsupported product claims, excluded"}, {"url":"https://www.scribd.com/document/599431326/Tribute-to-Strategists", "reason":"Reupload/permission and complete access unknown; not used as training source"}, {"url":"https://rutube.ru/video/2616c87d1d5f8516f78237aa95caa29e/", "reason":"Third-party tournament reupload rights and original authorship unresolved; not downloaded or treated as demonstration"}],
 "limitations":["No video watched or subtitles extracted", "No authenticated expert replay/state trajectory obtained", "A named strategy author is not automatically a verified professional player", "Source claims alone do not establish VCMI equivalence or policy improvement"]}
for name, obj in [("registry.json", registry), ("pilots.json", {"schema_version":1,"candidates":pilots,"candidate_count":len(pilots),"engine_verified_count":0,"bc_used_count":0})]:
    (ROOT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")

rows = ["# 专家来源与试点目录", "", "已整理 11 个来源记录、15 个试点候选。E2 表示实际读到作者的明确文字建议；E1 仅有题名/简介/章节；E0 仅确认频道。没有完成视频观看、字幕提取或高手动作轨迹提取。病例复现及训练结果须见单独执行证据，本目录不自动升级其状态。", "", "最可行的首例是 Richard Hallas 于 2001 年公开发表的 Complete 攻略中的龙反击友伤。定位和17词短引文见 source_case.json；原文为具名实质攻略，不等于认证职业选手比赛录像。阿青仍为优先研究对象，但可访问章节线索不足以重建他的实际操作。", "", "## 来源", ""]
for s in sources:
    rows += [f"- **{s['id']}** [{s['title']}]({s['url']}) — {s['author']}，{s['published_at'] or '发布日期未知'}，{s['evidence_level']}。{s['access_observed']}"]
rows += ["", "## 15个候选", "", "|编号|候选|证据及当前范围|", "|---|---|---|"]
for p in pilots:
    rows += [f"|{p['id']}|{p['tactic_name']}|{p['extraction_status']}；{p['scope']}|"]
rows += ["", "## 筛选与限制", "", "按可定位原始证据、规则可验证性、当前接口适用性筛选；不以播放量决定真伪。标题线索不生成专家动作。没有字幕/存档的内容保留未知，具体兵力和坐标由实验创建时必须标明实验重建。", "", "B站直接页面访问出现 HTTP 412/读取失败，因此只使用公开搜索索引显示的原发布元数据，没有绕过限制。YouTube/Twitch只返回频道外壳，没有获取VOD或字幕。没有下载或再分发视频。B站页面注明未经授权禁止转载；来源许可未知，不声称拥有视频/完整字幕训练授权。", "", "Complete、SoD、HotA及VCMI需分别记录版本。龙喷吐方向与双格占位必须由固定版本真实执行核验；旧AI发呆漏洞不代表VCMI BattleAI也有。英雄主动施法、飞跳回、兵链、技能和经济暂归后续/战略档案。", "", "要进一步做阿青、Lexiav等真实操作提取，需要可合法读取的字幕/讲解文本、明确时间定位或获许可的存档/回放。任何输入仍需确认版本、可观测状态和动作合法性；不依赖视频坐标猜测。", ""]
(ROOT/"SOURCES_AND_PILOTS.md").write_text("\n".join(rows), encoding="utf-8")
print(json.dumps({"source_count":len(sources),"pilot_count":len(pilots),"output":str(ROOT)},ensure_ascii=False))
