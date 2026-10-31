/*
 * CDirectorAI.cpp, part of the Heroes3-AI-Lab adventure layer.
 *
 * Strategy baseline: send the freshest owned hero toward the nearest *visible* enemy hero,
 * else the nearest *visible* enemy town, else a deterministic scouting waypoint. Battles are
 * delegated to a native battle AI through CAdventureAI::getBattleAIName().
 *
 * Visibility rules (verified against lib/callback/CPlayerSpecificInfoCallback):
 *   - getHeroesInfo() returns ONLY our own heroes, so enemies cannot be found through it.
 *   - getTownsInfo() defaults to onlyOur=true; onlyOur=false returns visible towns.
 *   - enemy heroes are enumerated from map objects and filtered with cb->isVisible(), i.e. the
 *     engine's own fog-of-war check. Hidden objects are never inspected.
 *
 * Turn protocol: moveHero() issues an asynchronous request. The turn must not be ended in the
 * same call, and heroMoved() is a global receiver that also sees the opponent's moves, so the
 * pending request is tracked by hero id and only that hero's move may advance our turn.
 */
#include "StdInc.h"
#include "CDirectorAI.h"

#include "../../lib/CStack.h"
#include "../../lib/battle/BattleAction.h"
#include "../../lib/callback/CCallback.h"
#include "../../lib/mapObjects/CGHeroInstance.h"
#include "../../lib/mapObjects/CGTownInstance.h"
#include "../../lib/mapObjects/CGCreature.h"
#include "../../lib/networkPacks/PacksForClient.h"
#include "../../lib/networkPacks/PacksForServer.h"
#include "../../lib/serializer/CTypeList.h"
#include "../../lib/gameState/EVictoryLossCheckResult.h"
#include "../../lib/CCreatureHandler.h"
#include "../../lib/gameState/InfoAboutArmy.h"
#include "../../lib/LogicalExpression.h"
#include "../../lib/callback/Calendar.h"
#include <fstream>
#include <cstdlib>
#include <cstdio>
#include <thread>
#include <chrono>
#include "../../lib/pathfinder/CGPathNode.h"
#include "../../lib/pathfinder/PathfinderCache.h"

namespace
{
	int distanceSquared(const int3 & a, const int3 & b)
	{
		const int dx = a.x - b.x;
		const int dy = a.y - b.y;
		return dx * dx + dy * dy;
	}
}

void CDirectorAI::initGameInterface(std::shared_ptr<Environment> ENV, std::shared_ptr<CCallback> CB, AutocombatPreferences AP)
{
	cb = CB;
	if(std::getenv("LAB_ADV_AGENT_DIR") || !std::getenv("LAB_HERO_PROBE_LOG"))
		throw std::runtime_error("Engineering probe requires own log and forbids policy broker");
	env = ENV;
	autocombatPreferences = AP;
	human = false;
	playerID = *cb->getPlayerID();
	pathfinderOptions = std::make_unique<PathfinderOptions>(*cb);
	pathfinder = std::make_unique<PathfinderCache>(cb.get(), *pathfinderOptions);
	logGlobal->info("DirectorAI: game interface ready for player %s", playerID.toString());
}

void CDirectorAI::initBattleInterface(std::shared_ptr<Environment> ENV, std::shared_ptr<CBattleCallback> CB, AutocombatPreferences AP)
{
	// CAdventureAI::battleStart dereferences the inherited cbc to suspend/restore waitTillRealize.
	cbc = CB;
	env = ENV;
	autocombatPreferences = AP;
	logGlobal->info("DirectorAI: battle callback %s", cbc ? "installed" : "MISSING");
}

std::string CDirectorAI::getBattleAIName() const
{
	// Native battle AI handles every encounter; the director never acts inside a battle.
	return "BattleAI";
}

const CGHeroInstance * CDirectorAI::pickHero(std::vector<const CGHeroInstance *> & heroes) const
{
    if(probeMeetingSeen || probeFailed || probeEndAck) return nullptr;
    const CGHeroInstance * selected = nullptr;
    for(const auto * hero : heroes)
        if(hero && hero->getOwner() == playerID && !hero->isGarrisoned() &&
           !blockedHeroes.count(hero->id.getNum()) && hero->movementPointsRemaining() > 0 &&
           (!selected || hero->id.getNum() < selected->id.getNum())) selected = hero;
    return selected;
}

bool CDirectorAI::findTarget(const CGHeroInstance * hero, int3 & destination, std::string & reason) const
{
    const auto heroes = cb->getHeroesInfo();
    if(heroes.size() != 2) { probeEvent("fixture_hero_count_invalid"); return false; }
    const CGHeroInstance * other = nullptr;
    for(const auto * candidate : heroes)
        if(candidate && candidate != hero && candidate->getOwner() == playerID && !candidate->isGarrisoned()) other = candidate;
    if(!other || other->visitablePos() == hero->visitablePos()) { probeEvent("fixture_target_invalid"); return false; }
    CGPath path;
    pathfinder->invalidatePaths();
    if(!pathfinder->getPathsInfo(hero)->getPath(path, other->visitablePos()) ||
       !path.hasNextNode() || path.nextNode().turns != 0 || path.nextNode().coord == hero->visitablePos())
       { probeEvent("fixture_no_real_path"); return false; }
    destination = other->visitablePos();
    reason = "PURE_ENGINEERING_actual_owned_hero_meeting";
    return true;
}

bool CDirectorAI::issueMove()
{
	// Hard cap per turn so a stuck target can never turn into an unbounded loop.
	if(movesThisTurn >= 8)
	{
		logGlobal->info("DirectorAI: move budget for this turn exhausted (%d)", movesThisTurn);
		return false;
	}

	std::vector<const CGHeroInstance *> heroes = cb->getHeroesInfo();
	const CGHeroInstance * hero = pickHero(heroes);
	if(!hero)
	{
		logGlobal->info("DirectorAI: no hero with movement points");
		return false;
	}

	int3 destination(-1, -1, -1);
	std::string reason;
	if(!findTarget(hero, destination, reason))
	{
		logGlobal->info("DirectorAI: no target for hero %d", hero->id.getNum());
		blockedHeroes.insert(hero->id.getNum());
		return issueMove();
	}

	const int3 here = hero->visitablePos();
	int3 step = destination;
	bool zeroLength = false;

	if(here == destination)
	{
		// A zero-length move is the legal way to visit / fight the object standing on the
		// current tile (this is what Nullkiller2 does too). It is not a failure.
		zeroLength = true;
	}
	else
	{
		CGPath path;
		pathfinder->invalidatePaths();
		pathfinder->getPathsInfo(hero)->getPath(path, destination);
		if(!path.hasNextNode())
		{
			logGlobal->info("DirectorAI: hero %d cannot reach %s reason=%s",
				hero->id.getNum(), destination.toString(), reason);
			return false;
		}
		const CGPathNode next = path.nextNode();
		if(next.turns != 0)
		{
			logGlobal->info("DirectorAI: %s not reachable this turn (turns=%d) reason=%s",
				destination.toString(), static_cast<int>(next.turns), reason);
			return false;
		}
		step = next.coord;
	}

	// Targets are in visitable coordinates; the request needs the hero's object coordinates.
	pendingHero = hero->id;
	pendingMove = true;
	lastStep = step;
	++movesThisTurn;
	logGlobal->info("DirectorAI: step hero %d %s -> %s reason=%s%s",
		hero->id.getNum(), here.toString(), step.toString(), reason,
		zeroLength ? " (interact with current tile)" : "");
	traceState("before_move");
	probeEvent("move_issued");
	cb->moveHero(hero, hero->convertFromVisitablePos(step), false, EPathfindingLayer::LAND);
	return true;
}

void CDirectorAI::yourTurn(QueryID queryID)
{
    if(probeEndAck) { probeEvent("unexpected_additional_turn"); return; }
	pendingMove = false;
	pendingHero = ObjectInstanceID();
	turnActive = true;
	endingTurn = false;
	battleBusy = false;
	movementBusy = false;
	blockedHeroes.clear();
	committedTargets.clear();
	recruitedThisTurn.clear();
	++ownTurns;
	traceState("turn_start");
	if(!savedInitial)
	{
		savedInitial = true;
		probeEvent("save_disabled");
	}
	movesThisTurn = 0;
	if(queryID != QueryID(-1))
	{
		pendingQueries.insert(queryID);
		cb->selectionMade(0, queryID);
	}
	probeEvent("turn_open");
	advanceTurn();
}

void CDirectorAI::advanceTurn()
{
	if(!turnActive || endingTurn || pendingMove || pendingEconomy || battleBusy || movementBusy ||
		!pendingQueries.empty() || !queryRequests.empty())
		return;
	if(issueEconomy())
		return;
	if(!issueMove())
		finishTurn();
}

void CDirectorAI::finishTurn()
{
	if(!turnActive)
		return;
	endingTurn = true;
	traceState("turn_end");
	cb->endTurn();
}

void CDirectorAI::heroMoved(const TryMoveHero & details, bool verbose)
{
	if(!turnActive || !pendingMove)
		return;
	// heroMoved is global: ignore every hero that is not the one we sent.
	if(!(details.id == pendingHero))
		return;

	logGlobal->info("DirectorAI: step finished result=%d points_left=%d from %s to %s",
		static_cast<int>(details.result), details.movePoints,
		details.start.toString(), details.end.toString());

	if(details.result == TryMoveHero::FAILED || details.start == details.end)
		blockedHeroes.insert(details.id.getNum());
	// Observation only. The request acknowledgment and query/battle state drive scheduling.
}

void CDirectorAI::requestRealized(PackageApplied * pa)
{
    if(pa->player == playerID && probeTransferPending && static_cast<int>(pa->requestID) == probeTransferRequest)
    {
        probeTransferPending = false;
        pendingEconomy = false;
        if(!pa->result) probeFailed = true;
        traceState("probe_after_transfer");
        probeEvent("transfer_ack", static_cast<int>(pa->requestID), pa->result);
        probeClose(); // Always release real query after recording success or failure.
        return;
    }
    if(pa->player == playerID && static_cast<int>(pa->requestID) == probeCloseRequest && probeCloseRequest >= 0)
    {
        probeCloseAck = pa->result;
        if(!pa->result) probeFailed = true;
        queryRequests.erase(static_cast<int>(pa->requestID));
        if(pa->result) pendingQueries.erase(probeQuery);
        traceState("probe_after_close");
        probeEvent("close_ack", static_cast<int>(pa->requestID), pa->result);
        advanceTurn();
        return;
    }
    if(pa->player == playerID && pa->packType == CTypeList::getInstance().getTypeID<EndTurn>(nullptr))
    {
        probeEndAck = pa->result;
        probeEvent("endturn_ack", static_cast<int>(pa->requestID), pa->result);
        traceState("probe_endturn_ack");
        if(pa->result && probeCloseAck && probeResolved && !probeFailed &&
           !pendingMove && pendingQueries.empty() && queryRequests.empty() && !probeTransferPending)
            probeEvent("probe_completed_nonterminal", static_cast<int>(pa->requestID), 1);
    }

	if(pa->player != playerID)
		return;
	if(pendingEconomy && static_cast<int>(pa->requestID) == economyRequest)
	{
		pendingEconomy = false;
		logGlobal->info("DirectorAI: economy request finished id=%d success=%d", economyRequest, pa->result);
		traceState(pa->result ? "economy_applied" : "economy_failed");
		advanceTurn();
	}
	auto query = queryRequests.find(pa->requestID);
	if(query != queryRequests.end())
	{
		if(pa->result)
			pendingQueries.erase(query->second);
		queryRequests.erase(query);
		advanceTurn();
	}
	if(pa->packType == CTypeList::getInstance().getTypeID<MoveHero>(nullptr) && pendingMove)
	{
		pendingMove = false;
		traceState(pa->result ? "move_applied" : "move_failed");
		if(!pa->result)
			blockedHeroes.insert(pendingHero.getNum());
		advanceTurn();
	}
	if(pa->packType == CTypeList::getInstance().getTypeID<EndTurn>(nullptr) && endingTurn)
	{
		endingTurn = false;
		if(pa->result)
			turnActive = false;
	}
}

void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)
{
    if(dynamic_cast<const MoveHero *>(pack)) probeEvent("move_sent", requestID, -1);
    if(dynamic_cast<const EndTurn *>(pack)) probeEvent("endturn_sent", requestID, -1);
    if(probeTransferPending && dynamic_cast<const ArrangeStacks *>(pack))
    { probeTransferRequest = requestID; probeEvent("transfer_sent", requestID, -1); }
    if(auto reply = dynamic_cast<const QueryReply *>(pack))
        if(probeMeetingSeen && reply->qid == probeQuery)
        { probeCloseRequest = requestID; probeEvent("close_sent", requestID, -1); }

	if(auto reply = dynamic_cast<const QueryReply *>(pack))
		queryRequests[requestID] = reply->qid;
	if(pendingEconomy && (dynamic_cast<const BuildStructure *>(pack) ||
		dynamic_cast<const RecruitCreatures *>(pack) || dynamic_cast<const ArrangeStacks *>(pack) ||
		dynamic_cast<const HireHero *>(pack)))
		economyRequest = requestID;
}

void CDirectorAI::queryResolved(QueryID queryID)
{
    if(probeMeetingSeen && queryID == probeQuery) { probeResolved = true; probeEvent("exchange_query_resolved"); }
	pendingQueries.erase(queryID);
	// Chained level-up prompts follow QueryResolved but precede the reply ACK.
	// requestRealized resumes only after those preceding packs are consumed.
}

void CDirectorAI::playerBlocked(int reason, bool start)
{
	if(reason == PlayerBlocked::UPCOMING_BATTLE)
	{
		battleBusy = start;
		traceState(start ? "native_battle_blocked" : "native_battle_ready");
		if(!start)
			advanceTurn();
	}
	if(reason == PlayerBlocked::ONGOING_MOVEMENT)
	{
		movementBusy = start;
		traceState(start ? "native_movement_blocked" : "native_movement_unblocked");
		if(!start)
			advanceTurn();
	}
}

void CDirectorAI::battleEnded()
{
	// Isolated server emits UPCOMING_BATTLE END after the complete request,
	// deferred queries and victory checks. BattleEnded alone is not readiness.
}

void CDirectorAI::gameOver(PlayerColor player, const EVictoryLossCheckResult & result)
{
	logGlobal->info("DirectorAI: native gameOver player=%s victory=%d loss=%d",
		player.toString(), result.victory(), result.loss());
	if(player == playerID)
	{
		traceState(result.victory() ? "victory" : "defeat");
		turnActive = false;
	}
}

bool CDirectorAI::issueEconomy()
{ return false; }

void CDirectorAI::traceState(const std::string & event) const
{
	const auto * path = std::getenv("LAB_ADV_TRACE");
	if(!path)
		return;
	std::ofstream out(path, std::ios::app);
	out << "{\"event\":\"" << event << "\",\"player\":" << static_cast<int>(playerID.getNum())
		<< ",\"day\":" << cb->getCalendar().getCurrentDay()
		<< ",\"own_turn\":" << ownTurns << ",\"gold\":" << cb->getResourceAmount(GameResID::GOLD)
		<< ",\"wood\":" << cb->getResourceAmount(GameResID::WOOD)
		<< ",\"ore\":" << cb->getResourceAmount(GameResID::ORE) << ",\"heroes\":[";
	bool first = true;
	for(const auto * hero : cb->getHeroesInfo())
	{
		if(!first) out << ',';
		first = false;
		out << "{\"id\":" << hero->id.getNum() << ",\"x\":" << hero->visitablePos().x
			<< ",\"y\":" << hero->visitablePos().y << ",\"z\":" << hero->visitablePos().z
			<< ",\"movement\":" << hero->movementPointsRemaining() << ",\"army\":[";
		bool firstStack = true;
		for(const auto & slot : hero->Slots())
		{
			if(!firstStack) out << ',';
			firstStack = false;
			out << '[' << slot.second->getCreatureID().getNum() << ',' << slot.second->getCount() << ']';
		}
		out << "]}";
	}
	out << "],\"towns\":[";
	first = true;
	for(const auto * town : cb->getTownsInfo())
	{
		if(!first) out << ',';
		first = false;
		out << "{\"id\":" << town->id.getNum() << ",\"buildings\":[";
		bool firstBuilding = true;
		for(int b = 0; b < 44; ++b)
			if(town->hasBuilt(BuildingID(b)))
			{
				if(!firstBuilding) out << ',';
				firstBuilding = false;
				out << b;
			}
		out << "],\"army\":[";
		bool firstStack = true;
		for(const auto & slot : town->getUpperArmy()->Slots())
		{
			if(!firstStack) out << ',';
			firstStack = false;
			out << '[' << slot.second->getCreatureID().getNum() << ',' << slot.second->getCount() << ']';
		}
		out << "],\"available\":[";
		bool firstOffer = true;
		for(const auto & offer : town->creatures)
		{
			if(!firstOffer) out << ',';
			firstOffer = false;
			out << offer.first;
		}
		out << "]}";
	}
	out << "]}\n";
}





void CDirectorAI::heroGotLevel(const CGHeroInstance *hero, PrimarySkill pskill, std::vector<SecondarySkill> &skills, QueryID queryID)
{
	pendingQueries.insert(queryID);
	cb->selectionMade(0, queryID);
}

void CDirectorAI::commanderGotLevel(const CCommanderInstance * commander, std::vector<ui32> skills, QueryID queryID)
{
	pendingQueries.insert(queryID);
	cb->selectionMade(0, queryID);
}

void CDirectorAI::showBlockingDialog(const std::string &text, const std::vector<Component> &components, QueryID askID, const int soundID, bool selection, bool cancel, bool safeToAutoaccept)
{
	pendingQueries.insert(askID);
	// Native yes/no uses 1=yes, 0=no; selection components are indexed 1..N.
	// The macro policy already chose this visit. A zero reply silently cancels it.
	const int answer = (selection && !components.empty()) || (!selection && cancel) ? 1 : 0;
	logGlobal->info("DirectorAI: dialog query=%d selection=%d cancel=%d components=%d answer=%d",
		askID.getNum(), selection, cancel, static_cast<int>(components.size()), answer);
	cb->selectionMade(answer, askID);
}

void CDirectorAI::showTeleportDialog(const CGHeroInstance * hero, TeleportChannelID channel, TTeleportExitsList exits, bool impassable, QueryID askID)
{
	pendingQueries.insert(askID);
	cb->selectionMade(0, askID);
}

void CDirectorAI::showGarrisonDialog(const CArmedInstance * up, const CGHeroInstance * down, bool removableUnits, QueryID queryID, const MetaString & customTitle)
{
	pendingQueries.insert(queryID);
	cb->selectionMade(0, queryID);
}

void CDirectorAI::showMapObjectSelectDialog(QueryID askID, const Component & icon, const MetaString & title, const MetaString & description, const std::vector<ObjectInstanceID> & objects)
{
	pendingQueries.insert(askID);
	cb->selectionMade(0, askID);
}

std::optional<BattleAction> CDirectorAI::makeSurrenderRetreatDecision(const BattleID & battleID, const BattleStateInfoForRetreat & battleState)
{
	// Never surrender or retreat: the director treats every battle as worth fighting.
	return std::nullopt;
}


void CDirectorAI::probeEvent(const std::string & event, int request, int result) const
{
    const char * path = std::getenv("LAB_HERO_PROBE_LOG");
    if(!path) return;
    std::ofstream out(path, std::ios::app);
    out << "{\"schema\":\"multihero-native-mechanism-probe-v1\",\"variant\":\"transfer-close\",\"event\":\"" << event
        << "\",\"request_id\":" << request << ",\"result\":" << result
        << ",\"query_id\":" << probeQuery.getNum() << ",\"pending_move\":" << pendingMove
        << ",\"pending_queries\":" << pendingQueries.size() << ",\"query_requests\":" << queryRequests.size()
        << ",\"courier\":" << probeCourier.getNum() << ",\"receiver\":" << probeReceiver.getNum()
        << ",\"failed\":" << probeFailed << ",\"own_turn\":" << ownTurns << "}\n";
}

void CDirectorAI::probeClose()
{
    probeEvent("close_requested");
    cb->selectionMade(0, probeQuery);
}

void CDirectorAI::heroExchangeStarted(ObjectInstanceID hero1, ObjectInstanceID hero2, QueryID queryID)
{
    probeMeetingSeen = true;
    probeCourier = hero1;
    probeReceiver = hero2;
    probeQuery = queryID;
    probeEvent("exchange_callback");
    traceState("probe_before_exchange");
    
    pendingQueries.insert(queryID);
    if(true)
    {
        const CGHeroInstance * donor = nullptr;
        const CGHeroInstance * receiver = nullptr;
        for(const auto * hero : cb->getHeroesInfo())
        {
            if(hero->id == hero1) donor = hero;
            if(hero->id == hero2) receiver = hero;
        }
        if(!donor || !receiver || donor->getOwner() != playerID || receiver->getOwner() != playerID ||
           donor->stacksCount() < 2 || receiver->stacksCount() < 1)
        {
            probeFailed = true; probeEvent("transfer_fixture_invalid"); probeClose(); return;
        }
        for(const auto & stack : donor->Slots())
        {
            const auto slot = receiver->getSlotFor(stack.second->getCreatureID());
            if(!slot.validSlot()) continue;
            // Whole one-stack transfer leaves donor's other stack and receiver's original army.
            probeTransferPending = true;
            pendingEconomy = true;
            traceState("probe_before_transfer");
            probeEvent("transfer_requested");
            cb->mergeOrSwapStacks(donor, receiver, stack.first, slot);
            return; // Query remains open until this exact ArrangeStacks request ACK.
        }
        probeFailed = true; probeEvent("transfer_no_legal_slot");
    }
    probeClose();
}
