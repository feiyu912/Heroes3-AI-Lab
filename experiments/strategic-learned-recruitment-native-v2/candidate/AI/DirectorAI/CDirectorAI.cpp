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
#include "TypedPolicyProtocol.h"
#include <iterator>
#include "../../lib/entities/faction/CTown.h"
#include "../../lib/entities/building/CBuilding.h"

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
#include <tuple>
#include "../../lib/pathfinder/CGPathNode.h"
#include "../../lib/pathfinder/PathfinderCache.h"

namespace
{
 std::map<int,std::int64_t> armyTotals(const CArmedInstance * army)
 {
  std::map<int,std::int64_t> totals;
  if(army) for(const auto & slot:army->Slots()) totals[slot.second->getCreatureID().getNum()]+=slot.second->getCount();
  return totals;
 }
 template<class Resources> std::array<std::int64_t,7> resourceTotals(const Resources & values)
 { std::array<std::int64_t,7> result{};for(unsigned i=0;i<7;++i) result[i]=values[i];return result; }
 std::string armySlotsJSON(const CArmedInstance * army)
 {
  std::ostringstream out;out << '[';
  for(int i=0;i<7;++i)
  {
   if(i) out << ',';const CStackInstance * stack=(army && army->hasStackAtSlot(SlotID(i))) ? army->getStackPtr(SlotID(i)) : nullptr;
   if(!stack) out << "null";
   else out << "{\"slot\":" << i << ",\"creature_id\":" << stack->getCreatureID().getNum() << ",\"count\":" << stack->getCount() << '}';
  }
  out << ']';return out.str();
 }
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
	env = ENV;
	autocombatPreferences = AP;
	human = false;
	playerID = *cb->getPlayerID();
 try { learnedRecruitEnabled=LabLearnedRecruit::enabled(std::getenv("LAB_ADV_LEARNED_ECONOMY"));learnedBuildEnabled=learnedRecruitEnabled || LabLearnedBuild::enabled(std::getenv("LAB_ADV_LEARNED_ECONOMY")); }
 catch(...) { typedFailure("invalid_learned_build_mode");return; }
 if(learnedRecruitEnabled) logGlobal->info("DirectorLearnedEconomyEpoch player=%d epoch=learned-economy-build-recruit-v1 schema=strategy-candidates-v6",playerID.getNum());
 else if(learnedBuildEnabled) logGlobal->info("DirectorLearnedEconomyEpoch player=%d epoch=learned-economy-build-v1 schema=strategy-candidates-v5",playerID.getNum());
 if(learnedRecruitEnabled && !exportCreatureCatalog()) return;
 const auto * replanMode=std::getenv("LAB_ADV_THREAT_REPLAN");
 const std::string mode=replanMode ? replanMode : "off";
 if(mode!="off" && mode!="once") { typedFailure("invalid_threat_replan_mode");return; }
 threatReplanEnabled=mode=="once";
 logGlobal->info("DirectorThreatReplanMode player=%d mode=%s",playerID.getNum(),mode);

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
	const CGHeroInstance * best = nullptr;
	int bestMovement = 0;
	for(const auto * hero : heroes)
	{
		if(!hero || hero->getOwner() != playerID || blockedHeroes.count(hero->id.getNum()))
			continue;
		const int movement = hero->movementPointsRemaining();
		if(movement > bestMovement)
		{
			bestMovement = movement;
			best = hero;
		}
	}
	return best;
}

bool CDirectorAI::findTarget(const CGHeroInstance * hero, int3 & destination, std::string & reason) const
{
	if(!std::getenv("LAB_ADV_AGENT_DIR")) { typedFailure("missing_agent_directory");return false; }
	bool found = false;
	candidates.clear();
	visibleThreats.clear();
	selectedCandidate = -1;
	double bestScore = -1;
	pathfinder->invalidatePaths();
	auto paths = pathfinder->getPathsInfo(hero);
	auto audit = [&](const int3 & pos, int kind, const std::string & status, double strength)
	{
		const auto * trace = std::getenv("LAB_ADV_TRACE");
		if(!trace) return;
		std::ofstream out(std::string(trace) + ".targets.jsonl", std::ios::app);
		const auto * node = paths->getPathInfo(pos);
		out << "{\"day\":" << cb->getCalendar().getCurrentDay() << ",\"hero\":" << hero->id.getNum()
			<< ",\"kind\":" << kind << ",\"position\":[" << pos.x << ',' << pos.y << ',' << pos.z
			<< "],\"status\":\"" << status << "\",\"strength\":" << strength
			<< ",\"own_strength\":" << ArmyDescriptor(hero, true).getStrength()
			<< ",\"tile_visible\":" << cb->isVisible(pos)
			<< ",\"turns\":" << static_cast<int>(node->turns)
			<< ",\"accessibility\":" << static_cast<int>(node->accessible)
			<< ",\"from\":[" << hero->visitablePos().x << ',' << hero->visitablePos().y << ',' << hero->visitablePos().z
			<< "]}\n";
	};
	auto consider = [&](const int3 & pos, double benefit, const std::string & why, int kind)
	{
		if(pos == hero->visitablePos())
			return;
		CGPath path;
		if(!paths->getPath(path, pos) || !path.hasNextNode() || path.nextNode().turns != 0)
		{
			if(kind < 2) audit(pos, kind, "no_current_turn_path", -1);
			return;
		}
		if(kind < 2) audit(pos, kind, "candidate", -1);
		const double score = benefit / (0.5 + path.lastNode().cost);
		candidates.push_back({pos, path.nextNode().coord, kind, path.lastNode().cost, score});
		if(score > bestScore)
		{
			bestScore = score;
			selectedCandidate = static_cast<int>(candidates.size()) - 1;
			destination = pos;
			reason = why;
			found = true;
		}
	};
	// This callback itself filters by player visibility. Never inspect hidden object containers.
	for(const auto * obj : cb->getAllVisitableObjs())
	{
		if(obj->getOwner().isValidPlayer() && obj->getOwner() != playerID &&
			cb->getPlayerRelations(playerID, obj->getOwner()) != PlayerRelations::ENEMIES)
			continue;
		if(obj->ID == Obj::MONSTER && cb->isVisible(obj->visitablePos()))
		{
			const auto * monster = dynamic_cast<const CGCreature *>(obj);
			if(!monster) continue;
			const double strength = ArmyDescriptor(monster, false).getStrength();
			if(strength > ArmyDescriptor(hero, true).getStrength() * 0.8)
			{
				audit(obj->visitablePos(), 0, "neutral_strength_filter", strength);
				continue;
			}
			consider(obj->visitablePos(), 6, "visible neutral army clearance", 0);
		}
		else if(obj->ID == Obj::HERO && obj->getOwner() != playerID)
		{
			if(!cb->isVisible(obj->visitablePos()))
			{
				audit(obj->visitablePos(), 0, "visitable_tile_not_visible", -1);
				continue;
			}
			InfoAboutHero enemy;
			if(!cb->getHeroInfo(obj, enemy, hero))
			{
				audit(obj->visitablePos(), 0, "info_unavailable", -1);
				continue;
			}
			// Use the same approximate, disguise-aware army descriptor exposed to a player.
			visibleThreats.emplace_back(obj->visitablePos(), enemy.army.getStrength());
			if(enemy.army.getStrength() > ArmyDescriptor(hero, true).getStrength() * 0.9)
			{
				audit(obj->visitablePos(), 0, "strength_filter", enemy.army.getStrength());
				continue;
			}
			consider(obj->visitablePos(), 8, "visible enemy hero", 0);
		}
		else if(obj->ID == Obj::TOWN && obj->getOwner() != playerID)
		{
			InfoAboutTown enemy;
			if(!cb->getTownInfo(obj, enemy, hero))
			{
				audit(obj->visitablePos(), 1, "info_unavailable", -1);
				continue;
			}
			if(enemy.army.getStrength() > ArmyDescriptor(hero, true).getStrength() * 0.8)
			{
				audit(obj->visitablePos(), 1, "strength_filter", enemy.army.getStrength());
				continue;
			}
			consider(obj->visitablePos(), 12, "visible capturable town", 1);
		}
		else if(obj->ID == Obj::MINE && obj->getOwner() != playerID)
			consider(obj->visitablePos(), 7, "visible capturable mine", 2);
		else if(obj->ID == Obj::TOWN && obj->getOwner() == playerID)
		{
			const auto * town = dynamic_cast<const CGTownInstance *>(obj);
			if(town && town->getUpperArmy()->stacksCount() > 0)
				consider(obj->visitablePos(), 5, "own town reinforcements", 4);
		}
		else if(obj->ID == Obj::RESOURCE || obj->ID == Obj::TREASURE_CHEST || obj->ID == Obj::ARTIFACT)
			consider(obj->visitablePos(), 4, "visible pickup", 3);
	}
	// Explore only reachable known tiles bordering fog, rather than requesting a remote unseen goal.
	const int3 size = cb->getMapSize();
	for(int z = 0; z < size.z; ++z)
	{
		for(int y = 0; y < size.y; ++y)
		{
			for(int x = 0; x < size.x; ++x)
			{
				const int3 pos(x, y, z);
				if(!cb->isVisible(pos))
					continue;
				int unknown = 0;
				for(int dy = -1; dy <= 1; ++dy)
					for(int dx = -1; dx <= 1; ++dx)
						if(x + dx >= 0 && x + dx < size.x && y + dy >= 0 && y + dy < size.y &&
							!cb->isVisible(int3(x + dx, y + dy, z)))
							++unknown;
				if(unknown)
					consider(pos, 1 + unknown * 0.1, "reachable fog frontier", 5);
			}
		}
	}

	if(std::getenv("LAB_ADV_AGENT_DIR"))
	{
		// Keep a chosen destination within this turn while it remains an admissible goal.
		auto previous = committedTargets.find(hero->id.getNum());
		if(previous != committedTargets.end())
		{
			auto retained = std::find_if(candidates.begin(), candidates.end(), [&](const Candidate & c)
			{
				return c.destination == previous->second.first && c.kind == previous->second.second;
			});
			if(retained != candidates.end())
			{
				const Candidate committed = *retained;
                bool pressureNow=false;int3 trigger(-1,-1,-1);double enemyValue=0,ownValue=0;
                if(threatReplanEnabled && !threatReplanUsed.count(hero->id.getNum()) && candidates.size()>1)
                {
                    ownValue=ArmyDescriptor(hero,true).getStrength();const auto pos=hero->visitablePos();
                    for(const auto & threat:visibleThreats)
                        if(LabThreatReplan::pressure(pos.x,pos.y,pos.z,ownValue,threat.first.x,threat.first.y,threat.first.z,threat.second))
                        { pressureNow=true;trigger=threat.first;enemyValue=threat.second;break; }
                }
                if(LabThreatReplan::allowed(threatReplanEnabled,true,pressureNow,threatReplanUsed.count(hero->id.getNum()),candidates.size()))
                {
                    threatReplanUsed.insert(hero->id.getNum());
                    const auto pos=hero->visitablePos();std::ostringstream record;
                    record << "{\"event\":\"bounded_threat_replan\",\"player\":" << static_cast<int>(playerID.getNum())
                      << ",\"decision_id\":" << externalDecisionSerial+1 << ",\"own_turn\":" << ownTurns
                      << ",\"day\":" << cb->getCalendar().getCurrentDay() << ",\"hero\":" << hero->id.getNum()
                      << ",\"from\":[" << pos.x << ',' << pos.y << ',' << pos.z << "]"
                      << ",\"previous_goal\":[" << committed.destination.x << ',' << committed.destination.y << ',' << committed.destination.z
                      << "],\"previous_kind\":" << committed.kind << ",\"available_moves\":" << candidates.size()
                      << ",\"own_army_value\":" << ownValue << ",\"threat\":{\"position\":[" << trigger.x << ',' << trigger.y << ',' << trigger.z
                      << "],\"approx_army_value\":" << enemyValue << "}}";
                    logGlobal->info("DirectorThreatReplan %s",record.str());
                    if(const auto * trace=std::getenv("LAB_ADV_TRACE"))
                    { std::ofstream file(std::string(trace)+".replan.jsonl",std::ios::app);file << record.str() << '\n'; }
                }
                else candidates.assign(1, committed);
			}
		}
		if(learnedBuildEnabled && buildWindow.open) appendBuildCandidates();
  if(learnedRecruitEnabled && buildWindow.open) appendRecruitCandidates();
		Candidate stop{};stop.endTurn=true;candidates.push_back(stop);
		const int selected = chooseExternalCandidate(hero);
		if(selected < 0 || selected >= static_cast<int>(candidates.size()))
		{
			logGlobal->error("DirectorAI: external policy failed for hero %d", hero->id.getNum());
			return false;
		}
		selectedCandidate = selected;
		if(candidates[selected].endTurn) { reason="typed_end_turn";return true; }
  if(candidates[selected].build) { reason="typed_build";return true; }
  if(candidates[selected].recruit) { reason="typed_recruit";return true; }
		destination = candidates[selected].destination;
		committedTargets[hero->id.getNum()] = {destination, candidates[selected].kind};
		reason = "local candidate policy";
	}
	if(!found)
	{
		const auto * trace = std::getenv("LAB_ADV_TRACE");
		if(trace)
		{
			std::ofstream out(std::string(trace) + ".paths.jsonl", std::ios::app);
			out << "{\"day\":" << cb->getCalendar().getCurrentDay() << ",\"from\":["
				<< hero->visitablePos().x << ',' << hero->visitablePos().y << ',' << hero->visitablePos().z << "],\"neighbors\":[";
			bool first = true;
			for(int dy = -1; dy <= 1; ++dy)
				for(int dx = -1; dx <= 1; ++dx)
				{
					const int3 pos = hero->visitablePos() + int3(dx, dy, 0);
					if(pos.x < 0 || pos.y < 0 || pos.x >= size.x || pos.y >= size.y) continue;
					const auto * node = paths->getPathInfo(pos);
					if(!first) out << ',';
					first = false;
					out << "{\"x\":" << pos.x << ",\"y\":" << pos.y << ",\"visible\":" << cb->isVisible(pos)
						<< ",\"turns\":" << static_cast<int>(node->turns) << ",\"accessibility\":" << static_cast<int>(node->accessible) << '}';
				}
			out << "]}\n";
		}
	}
	return found;
}

bool CDirectorAI::issueMove()
{
	// Hard cap per turn so a stuck target can never turn into an unbounded loop.
	if(movesThisTurn >= MAX_MOVES_PER_TURN)
	{
		logGlobal->info("DirectorAI: move budget for this turn exhausted (%d)", movesThisTurn);
		return false;
	}

	std::vector<const CGHeroInstance *> heroes = cb->getHeroesInfo();
	if(heroes.size()>1) { typedFailure("single_hero_pilot_required");return false; }
	const CGHeroInstance * hero = pickHero(heroes);
 if(!hero && learnedBuildEnabled && buildWindow.open && heroes.size()==1) hero=heroes.front();
	if(!hero)
	{
		logGlobal->info("DirectorAI: no hero with movement points");
		return false;
	}

	int3 destination(-1, -1, -1);
	std::string reason;
	if(!findTarget(hero, destination, reason))
	{
		typedFailure("typed_target_selection_failed");return false;
	}

	if(!preparedTyped || preparedTyped->ownTurn!=ownTurns) { typedFailure("stale_prepared_action");return false; }
	if(learnedBuildEnabled)
 {
  if(!(learnedRecruitEnabled ? LabLearnedRecruit::select(buildWindow,preparedTyped->op) : buildWindow.select(preparedTyped->op))) { typedFailure("build_window_violation");return false; }
  if(candidates[selectedCandidate].build) return issuePolicyBuild();
  if(candidates[selectedCandidate].recruit) return issuePolicyRecruit();
 }
 if(candidates[selectedCandidate].endTurn) { finishTurn();return true; }
	emitTypedBusy();
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
			typedFailure("selected_move_path_changed");return false;
		}
		const CGPathNode next = path.nextNode();
		if(next.turns != 0)
		{
			logGlobal->info("DirectorAI: %s not reachable this turn (turns=%d) reason=%s",
				destination.toString(), static_cast<int>(next.turns), reason);
			typedFailure("selected_move_not_current_turn");return false;
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
	traceDecision(hero, destination, step);
	preparedTyped->objectStep=hero->convertFromVisitablePos(step);
	cb->moveHero(hero, hero->convertFromVisitablePos(step), false, EPathfindingLayer::LAND);
	return true;
}


void CDirectorAI::yourTurn(QueryID queryID)
{
 // The immutable typed tuple survives even if old EndTurn ACK is still in flight.
 if(!outstandingTyped)
 {
  pendingMove=false;pendingHero=ObjectInstanceID();battleBusy=false;movementBusy=false;
 }
 turnActive=true;endingTurn=false;blockedHeroes.clear();committedTargets.clear();threatReplanUsed.clear();recruitedThisTurn.clear();
 if(learnedRecruitEnabled) { if(pendingFreeTransfer) { typedFailure("new_turn_with_free_transfer_pending");return; }attemptedFreeTransferStates.clear(); }
 ++ownTurns;if(learnedBuildEnabled) buildWindow.begin(ownTurns);traceState("turn_start");
 emitTyped("{\"event\":\"your_turn\",\"player\":"+std::to_string(playerID.getNum())+",\"own_turn\":"+std::to_string(ownTurns)+"}");
 if(!savedInitial) { savedInitial=true;cb->save("Saves/director-v5-initial",false); }
 movesThisTurn=0;
 if(queryID!=QueryID(-1)) { pendingQueries.insert(queryID);cb->selectionMade(0,queryID); }
 advanceTurn();
}


void CDirectorAI::advanceTurn()
{
 emitTypedBusy();
 if(!turnActive || typedProtocolFailed || endingTurn || pendingMove || pendingEconomy || battleBusy || movementBusy ||
    !pendingQueries.empty() || !queryRequests.empty() || outstandingTyped || preparedTyped) return;
 if(learnedBuildEnabled && (buildWindow.open || learnedRecruitEnabled) && issueFreeArmyTransfer()) return;
 if((!learnedBuildEnabled || !buildWindow.open || cb->getHeroesInfo().empty()) && issueEconomy()) return;
 if(!issueMove()) finishTurn();
}


void CDirectorAI::finishTurn()
{
 if(!turnActive || typedProtocolFailed || outstandingTyped || pendingMove || pendingEconomy || battleBusy || movementBusy ||
    !pendingQueries.empty() || !queryRequests.empty()) return;
 if(preparedTyped && preparedTyped->op!="end_turn") { typedFailure("unconsumed_move_before_end_turn");return; }
 if(!preparedTyped)
 {
  TypedContext ctx;ctx.automatic=true;ctx.player=playerID.getNum();ctx.ownTurn=ownTurns;ctx.op="end_turn";
  const auto heroes=cb->getHeroesInfo();ctx.hero=heroes.empty() ? 0 : heroes.front()->id.getNum();
  ctx.candidateJSON="{\"op\":\"end_turn\"}";
  ctx.automaticReason=heroes.empty() ? "no_owned_hero" : (movesThisTurn>=MAX_MOVES_PER_TURN ? "native_move_budget" : "no_movable_hero");
  preparedTyped=ctx;
 }
 if(preparedTyped->ownTurn!=ownTurns) { typedFailure("stale_prepared_end_turn");return; }
 if(learnedRecruitEnabled) buildWindow.open=false;
 emitTypedBusy();endingTurn=true;traceState(preparedTyped->automatic ? "turn_end" : "before_end_turn");
 cb->endTurn(); // A genuine native EndTurn; never a same-position MoveHero.
}


void CDirectorAI::heroMoved(const TryMoveHero & details, bool verbose)
{
 if(!outstandingTyped || outstandingTyped->op!="move" || details.id.getNum()!=outstandingTyped->hero) return;
 if(outstandingTyped->moveResultSeen) { typedFailure("duplicate_move_result");return; }
 outstandingTyped->moveResultSeen=true;
 logGlobal->info("DirectorAI: step finished result=%d points_left=%d from %s to %s",static_cast<int>(details.result),
  details.movePoints,details.start.toString(),details.end.toString());
 // Evidence is the real received server TryMoveHero pack, not a fabricated reply.
 emitTypedAction("move_result",*outstandingTyped,",\"source\":\"server\",\"evidence\":\"received_TryMoveHero\",\"result\":"+std::to_string(static_cast<int>(details.result)));
 if(details.result==TryMoveHero::FAILED || details.start==details.end) blockedHeroes.insert(details.id.getNum());
 if(details.result==TryMoveHero::FAILED) typedFailure("native_move_failed");
}


void CDirectorAI::requestRealized(PackageApplied * pa)
{
 if(pa->player!=playerID) return;
 if(pendingEconomy && static_cast<int>(pa->requestID)==economyRequest)
 {
  if(learnedRecruitEnabled && pendingFreeTransfer)
  {
   const auto transfer=*pendingFreeTransfer;
   if(transfer.nativeRequestID!=static_cast<int>(pa->requestID) || pa->packType!=CTypeList::getInstance().getTypeID<ArrangeStacks>(nullptr))
   { typedFailure("free_transfer_ack_tuple_mismatch");return; }
   const bool changed=pa->result && verifyFreeTransferApplied(transfer);
   emitTyped("{\"event\":\"free_transfer_ack_state\",\"player\":"+std::to_string(playerID.getNum())+",\"native_request_id\":"+std::to_string(pa->requestID)+",\"success\":"+(pa->result ? "true" : "false")+",\"state_change_verified\":"+(changed ? "true" : "false")+",\"before_state\":"+transfer.beforeState+",\"state\":"+recruitTownState(transfer.townID)+"}");
   pendingFreeTransfer.reset();if(!changed) typedFailure("free_transfer_ack_without_exact_conservation");
  }
  pendingEconomy=false;logGlobal->info("DirectorAI: economy request finished id=%d success=%d",economyRequest,pa->result);
  traceState(pa->result ? "economy_applied" : "economy_failed");advanceTurn();
 }
 auto query=queryRequests.find(pa->requestID);
 if(query!=queryRequests.end())
 {
  if(pa->result) pendingQueries.erase(query->second);queryRequests.erase(query);advanceTurn();
 }
 const bool move=pa->packType==CTypeList::getInstance().getTypeID<MoveHero>(nullptr);
 const bool end=pa->packType==CTypeList::getInstance().getTypeID<EndTurn>(nullptr);
 const bool build=learnedBuildEnabled && pa->packType==CTypeList::getInstance().getTypeID<BuildStructure>(nullptr);
 const bool recruit=learnedRecruitEnabled && pa->packType==CTypeList::getInstance().getTypeID<RecruitCreatures>(nullptr);
 if(!move && !end && !build && !recruit) return;
 if(!outstandingTyped || outstandingTyped->nativeRequestID!=static_cast<int>(pa->requestID) ||
    outstandingTyped->op!=(move ? "move" : (build ? "build" : (recruit ? "recruit" : "end_turn")))) { typedFailure("unmatched_typed_ack");return; }
 const auto ctx=*outstandingTyped; // Save the old turn, never substitute the live ownTurns.
 if(build)
 {
  emitTypedAction("build_ack_state",ctx,",\"state\":"+buildTownState(ctx.townID));
  if(pa->result && !ctx.buildResultSeen) typedFailure("build_ack_without_received_structure");
 }
 if(recruit)
 {
  const bool changed=pa->result && verifyRecruitApplied(ctx);
  emitTypedAction("recruit_ack_state",ctx,std::string(",\"state_change_verified\":")+(changed ? "true" : "false")+",\"before_state\":"+ctx.beforeBuildState+",\"state\":"+recruitTownState(ctx.townID));
  if(!changed) typedFailure("recruit_ack_without_exact_state_change");
 }
 emitTypedAction("package_applied",ctx,std::string(",\"source\":\"client\",\"package\":\"PackageApplied\",\"success\":")+(pa->result ? "true" : "false"));
 outstandingTyped.reset(); // Only this exact native request/op ACK can clear the tuple.
 if(move)
 {
  pendingMove=false;traceState(pa->result ? "move_applied" : "move_failed");
  if(!pa->result) blockedHeroes.insert(ctx.hero);
 }
 else if(end && ctx.ownTurn==ownTurns)
 {
  endingTurn=false;if(pa->result) turnActive=false;
 }
 if(!pa->result) typedFailure("native_action_ack_failed");
 advanceTurn(); // A late old EndTurn ACK resumes the already-started new turn safely.
}


void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)
{
 if(auto reply=dynamic_cast<const QueryReply *>(pack)) queryRequests[requestID]=reply->qid;
 if(pendingEconomy && ((!learnedBuildEnabled && dynamic_cast<const BuildStructure *>(pack)) || (!learnedRecruitEnabled && dynamic_cast<const RecruitCreatures *>(pack)) ||
    dynamic_cast<const ArrangeStacks *>(pack) || dynamic_cast<const HireHero *>(pack))) economyRequest=requestID;
 if(learnedRecruitEnabled && pendingFreeTransfer)
 {
  const auto * actual=dynamic_cast<const ArrangeStacks *>(pack);auto & transfer=*pendingFreeTransfer;
  if(!actual || requestID<1 || pack->player!=playerID || static_cast<int>(pack->requestID)!=requestID || transfer.nativeRequestID!=-1 ||
     actual->id1.getNum()!=transfer.sourceArmyID || actual->id2.getNum()!=transfer.targetArmyID || actual->p1.getNum()!=transfer.fromSlot || actual->p2.getNum()!=transfer.toSlot || actual->what!=transfer.expectedWhat || actual->val!=0)
  { typedFailure("free_transfer_native_payload_mismatch");return; }
  transfer.nativeRequestID=requestID;
  emitTyped("{\"event\":\"free_transfer_native_sent\",\"player\":"+std::to_string(playerID.getNum())+",\"native_request_id\":"+std::to_string(requestID)+",\"source_army_id\":"+std::to_string(transfer.sourceArmyID)+",\"target_army_id\":"+std::to_string(transfer.targetArmyID)+",\"from_slot\":"+std::to_string(transfer.fromSlot)+",\"to_slot\":"+std::to_string(transfer.toSlot)+",\"creature_id\":"+std::to_string(transfer.creatureID)+",\"amount\":"+std::to_string(transfer.amount)+",\"actual_what\":"+std::to_string(actual->what)+",\"actual_val\":"+std::to_string(actual->val)+",\"before_state\":"+transfer.beforeState+"}");
 }
 const bool move=dynamic_cast<const MoveHero *>(pack)!=nullptr;
 const bool end=dynamic_cast<const EndTurn *>(pack)!=nullptr;
 const auto * actualBuild=dynamic_cast<const BuildStructure *>(pack);
 const bool build=learnedBuildEnabled && actualBuild;
 const auto * actualRecruit=dynamic_cast<const RecruitCreatures *>(pack);
 const bool recruit=learnedRecruitEnabled && actualRecruit;
 if(!move && !end && !build && !recruit) return;
 if(requestID<1 || !preparedTyped || outstandingTyped || preparedTyped->ownTurn!=ownTurns ||
    preparedTyped->op!=(move ? "move" : (build ? "build" : (recruit ? "recruit" : "end_turn")))) { typedFailure("unbound_native_request");return; }

 if(pack->player!=playerID || static_cast<int>(pack->requestID)!=requestID)
 { typedFailure("actual_native_request_identity_mismatch");return; }
 if(const auto * actual=dynamic_cast<const MoveHero *>(pack))
 {
  if(actual->hid.getNum()!=preparedTyped->hero || actual->path.size()!=1 || actual->path.front()!=preparedTyped->objectStep)
  { typedFailure("actual_native_move_payload_mismatch");return; }
 }
 if(build && (pendingEconomy || actualBuild->tid.getNum()!=preparedTyped->townID || actualBuild->bid.getNum()!=preparedTyped->buildingID))
 { typedFailure("actual_native_build_payload_mismatch");return; }
 if(recruit && (pendingEconomy || actualRecruit->tid.getNum()!=preparedTyped->townID || actualRecruit->dst.getNum()!=preparedTyped->destinationArmyID || actualRecruit->crid.getNum()!=preparedTyped->creatureID || actualRecruit->amount!=preparedTyped->amount || actualRecruit->level!=preparedTyped->level))
 { typedFailure("actual_native_recruit_payload_mismatch");return; }
 outstandingTyped=*preparedTyped;outstandingTyped->nativeRequestID=requestID;preparedTyped.reset();
 if(build)
 {
  const auto & ctx=*outstandingTyped;
  emitTypedAction("native_action_sent",ctx,",\"actual_request\":{\"pack_type\":\"BuildStructure\",\"player\":"+std::to_string(pack->player.getNum())+",\"native_request_id\":"+std::to_string(requestID)+",\"town_id\":"+std::to_string(actualBuild->tid.getNum())+",\"building_id\":"+std::to_string(actualBuild->bid.getNum())+"},\"before_state\":"+ctx.beforeBuildState);
 }
 else if(recruit)
 {
  const auto & ctx=*outstandingTyped;
  emitTypedAction("native_action_sent",ctx,",\"actual_request\":{\"pack_type\":\"RecruitCreatures\",\"player\":"+std::to_string(pack->player.getNum())+",\"native_request_id\":"+std::to_string(requestID)+",\"town_id\":"+std::to_string(actualRecruit->tid.getNum())+",\"destination_army_id\":"+std::to_string(actualRecruit->dst.getNum())+",\"creature_id\":"+std::to_string(actualRecruit->crid.getNum())+",\"amount\":"+std::to_string(actualRecruit->amount)+",\"level\":"+std::to_string(actualRecruit->level)+"},\"before_state\":"+ctx.beforeBuildState);
 }
 else emitTypedAction("native_action_sent",*outstandingTyped);
}

void CDirectorAI::queryResolved(QueryID queryID)
{
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
		emitTyped("{\"event\":\"game_over\",\"completed\":true,\"player\":"+std::to_string(playerID.getNum())+",\"own_turn\":"+std::to_string(ownTurns)+"}");
	}
}

bool CDirectorAI::issueFreeArmyTransfer()
{
 if(learnedRecruitEnabled) return issueFreeArmyTransferV6();
	for(const auto * town : cb->getTownsInfo())
	{
		const auto * army = town->getUpperArmy();
		if(auto hero = town->getVisitingHero())
		{
			if(hero->getOwner() == playerID && army != hero)
			{
				for(const auto & slot : army->Slots())
				{
					const auto key = std::make_pair(town->id.getNum(), 1000 + slot.second->getCreatureID().getNum());
					const auto targetSlot = hero->getSlotFor(slot.second->getCreatureID());
					if(!targetSlot.validSlot() || recruitedThisTurn.count(key))
						continue;
					recruitedThisTurn.insert(key);
					pendingEconomy = true;
					traceState("before_army_transfer");
					cb->mergeOrSwapStacks(army, hero, slot.first, targetSlot);
					return true;
				}
			}
		}
	}
	return false;
}

bool CDirectorAI::issueEconomy()
{
	for(const auto * town : cb->getTownsInfo())
	{
		if(cb->getHeroesInfo().empty() && town->hasBuilt(BuildingID::TAVERN) &&
			!town->getVisitingHero() && cb->getResourceAmount(GameResID::GOLD) >= GameConstants::HERO_GOLD_COST &&
			!recruitedThisTurn.count({town->id.getNum(), -2}))
		{
			recruitedThisTurn.insert({town->id.getNum(), -2});
			const auto offers = cb->getAvailableHeroes(town);
			if(!offers.empty())
			{
				pendingEconomy = true;
				traceState("before_hire_hero");
				cb->recruitHero(town, offers.front());
				return true;
			}
		}
  // New mode permits the existing no-hero rescue only; no scripted creature spending or legacy once-key transfer.
  if(learnedRecruitEnabled) continue;
		const BuildingID priorities[] = {BuildingID::TOWN_HALL, BuildingID::CITY_HALL,
			BuildingID::CAPITOL, BuildingID::TAVERN, BuildingID::MARKETPLACE,
			BuildingID::BLACKSMITH, BuildingID::MAGES_GUILD_1, BuildingID::FORT, BuildingID::DWELL_LVL_1,
			BuildingID::DWELL_LVL_2, BuildingID::DWELL_LVL_3, BuildingID::DWELL_LVL_4,
			BuildingID::DWELL_LVL_5, BuildingID::DWELL_LVL_6, BuildingID::DWELL_LVL_7,
			BuildingID::CITADEL, BuildingID::CASTLE};
		if(!learnedBuildEnabled) for(const auto building : priorities)
		{
			BuildingID selectedBuilding = building;
			auto state = cb->canBuildStructure(town, building);
			if(state == EBuildingState::PREREQUIRES && building.isDwelling())
			{
				const auto missing = town->genBuildingRequirements(building, true).getFulfillmentCandidates(
					[&](const BuildingID & id) { return town->hasBuilt(id); });
				const auto allowed = std::find_if(missing.begin(), missing.end(), [&](const BuildingID & id)
				{
					return cb->canBuildStructure(town, id) == EBuildingState::ALLOWED;
				});
				if(allowed == missing.end()) continue;
				selectedBuilding = *allowed;
				state = EBuildingState::ALLOWED;
			}
			if(state != EBuildingState::ALLOWED)
				continue;
			traceState("before_build");
			logGlobal->info("DirectorAI: build town=%d building=%d goal=%d",
				town->id.getNum(), selectedBuilding.getNum(), building.getNum());
			pendingEconomy = true;
			cb->buildBuilding(town, selectedBuilding);
			return true;
		}
		const auto * army = town->getUpperArmy();
		if(auto hero = town->getVisitingHero())
		{
			if(hero->getOwner() == playerID && army != hero)
			{
				for(const auto & slot : army->Slots())
				{
					const auto key = std::make_pair(town->id.getNum(), 1000 + slot.second->getCreatureID().getNum());
					const auto targetSlot = hero->getSlotFor(slot.second->getCreatureID());
					if(!targetSlot.validSlot() || recruitedThisTurn.count(key))
						continue;
					recruitedThisTurn.insert(key);
					pendingEconomy = true;
					traceState("before_army_transfer");
					cb->mergeOrSwapStacks(army, hero, slot.first, targetSlot);
					return true;
				}
			}
		}
		for(int level = static_cast<int>(town->creatures.size()) - 1; level >= 0; --level)
		{
			if(recruitedThisTurn.count({town->id.getNum(), level}))
				continue;
			recruitedThisTurn.insert({town->id.getNum(), level});
			const auto & offer = town->creatures[level];
			if(!offer.first || offer.second.empty())
				continue;
			const auto creature = offer.second.back();
			if(!army->getSlotFor(creature).validSlot())
				continue;
			const int amount = std::min<int>(offer.first,
				cb->getResourceAmount() / creature.toCreature()->getFullRecruitCost());
			if(amount <= 0)
				continue;
			traceState("before_recruit");
			logGlobal->info("DirectorAI: recruit town=%d creature=%d amount=%d level=%d",
				town->id.getNum(), creature.getNum(), amount, level);
			pendingEconomy = true;
			cb->recruitCreatures(town, army, creature, amount, level);
			return true;
		}
	}
	return false;
}

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

void CDirectorAI::traceDecision(const CGHeroInstance * hero, const int3 & destination, const int3 & step) const
{
	const auto * path = std::getenv("LAB_ADV_DECISIONS");
	if(!path)
		return;
	std::ofstream out(path, std::ios::app);
	out << "{\"schema\":\"strategy-candidates-v1\",\"player\":" << static_cast<int>(playerID.getNum())
		<< ",\"day\":" << cb->getCalendar().getCurrentDay() << ",\"hero\":" << hero->id.getNum()
		<< ",\"selected_candidate\":" << selectedCandidate
		<< ",\"from\":[" << hero->visitablePos().x << ',' << hero->visitablePos().y << ',' << hero->visitablePos().z
		<< "],\"destination\":[" << destination.x << ',' << destination.y << ',' << destination.z
		<< "],\"step\":[" << step.x << ',' << step.y << ',' << step.z << "],\"candidates\":[";
	bool first = true;
	for(const auto & c : candidates)
	{
		if(!first) out << ',';
		first = false;
		out << typedCandidateJSON(c);
	}
	out << "]}\n";
}


int CDirectorAI::chooseExternalCandidate(const CGHeroInstance * hero) const
{
 const auto * directory = std::getenv("LAB_ADV_AGENT_DIR");
 if(!directory || ownTurns < 1 || cb->getHeroesInfo().size() != 1 || preparedTyped || outstandingTyped)
 { typedFailure("invalid_policy_request_state");return -1; }
 if(externalDecisionSerial >= static_cast<unsigned>(std::numeric_limits<int>::max()))
 { typedFailure("decision_counter_overflow");return -1; }
 char suffix[32];std::snprintf(suffix,sizeof(suffix),"%08u.json",++externalDecisionSerial);
 const std::string request = std::string(directory) + "/request-" + suffix;
 const std::string response = std::string(directory) + "/action-" + suffix;
 std::ostringstream out;
 out << "{\"schema\":\"" << (learnedRecruitEnabled ? "strategy-candidates-v6" : (learnedBuildEnabled ? "strategy-candidates-v5" : "strategy-candidates-v4")) << "\",\"request_id\":" << externalDecisionSerial
  << ",\"player\":" << static_cast<int>(playerID.getNum()) << ",\"own_turn\":" << ownTurns << ",\"own_hero_count\":1"
  << ",\"day\":" << cb->getCalendar().getCurrentDay() << ",\"hero\":" << hero->id.getNum()
  << ",\"from\":[" << hero->visitablePos().x << ',' << hero->visitablePos().y << ',' << hero->visitablePos().z
  << "],\"gold\":" << cb->getResourceAmount(GameResID::GOLD) << ",\"wood\":" << cb->getResourceAmount(GameResID::WOOD)
  << ",\"ore\":" << cb->getResourceAmount(GameResID::ORE) << ",\"own_army_value\":" << ArmyDescriptor(hero,true).getStrength()
  << ",\"movement\":" << hero->movementPointsRemaining() << ",\"visible_threats\":[";
 bool first = true;
 for(const auto & threat : visibleThreats)
 {
  if(!first) out << ',';first=false;
  out << "{\"position\":[" << threat.first.x << ',' << threat.first.y << ',' << threat.first.z
   << "],\"approx_army_value\":" << threat.second << '}';
 }
 out << "]";
 if(learnedBuildEnabled) out << ",\"economy_epoch\":\"" << (learnedRecruitEnabled ? "learned-economy-build-recruit-v1" : "learned-economy-build-v1") << "\",\"economy_window_open\":" << (buildWindow.open ? "true" : "false") << ",\"resources\":" << LabLearnedBuild::resources(cb->getResourceAmount());
 if(learnedRecruitEnabled) out << ",\"creature_catalog_sha256\":\"" << creatureCatalogSHA << '"';
 out << ",\"own_towns\":[";first=true;
 for(const auto * town : cb->getTownsInfo())
 {
  if(!first) out << ',';first=false;const int3 pos=town->visitablePos();
  out << "{\"position\":[" << pos.x << ',' << pos.y << ',' << pos.z
   << "],\"army_value\":" << ArmyDescriptor(town->getUpperArmy(),true).getStrength();
  if(learnedBuildEnabled)
  {
   if(town->built<0 || town->getFactionID().getNum()<0) { typedFailure("invalid_own_town_state");return -1; }
   out << ",\"town_id\":" << town->id.getNum() << ",\"faction_id\":" << town->getFactionID().getNum() << ",\"built_today\":" << town->built << ",\"buildings\":" << LabLearnedBuild::ids(town->getBuildings());
   if(learnedRecruitEnabled) out << ",\"recruit_state\":" << recruitTownState(town->id.getNum());
  }
  out << '}';
 }
 out << "],\"candidates\":[";first=true;std::vector<std::string> operations;
 for(const auto & c : candidates)
 {
  if(!first) out << ',';first=false;out << typedCandidateJSON(c);
  operations.push_back(c.endTurn ? "end_turn" : (c.build ? "build" : (c.recruit ? "recruit" : "move")));
 }
 out << "]}\n";const auto requestBytes=out.str();const auto requestSHA=LabTypedPolicy::sha256(requestBytes);
 {
  std::ofstream file(request+".tmp",std::ios::binary);
  if(!file) { typedFailure("request_open_failed");return -1; }
  file << requestBytes;file.close();
  if(!file) { typedFailure("request_write_failed");return -1; }
 }
 if(std::rename((request+".tmp").c_str(),request.c_str())!=0)
 { typedFailure("request_publish_failed");return -1; }
 const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(30);
 while(std::chrono::steady_clock::now()<deadline)
 {
  std::ifstream file(response,std::ios::binary);
  if(file)
  {
   const std::string raw((std::istreambuf_iterator<char>(file)),std::istreambuf_iterator<char>());
   try
   {
    const auto selected=LabTypedPolicy::parseResponse(raw,static_cast<int>(externalDecisionSerial),playerID.getNum(),
       hero->id.getNum(),ownTurns,requestSHA,operations,learnedRecruitEnabled ? "strategy-typed-action-response-v3" : (learnedBuildEnabled ? "strategy-typed-action-response-v2" : "strategy-typed-action-response-v1"));
    TypedContext ctx;ctx.automatic=false;ctx.decisionID=static_cast<int>(externalDecisionSerial);
    ctx.player=playerID.getNum();ctx.hero=hero->id.getNum();ctx.ownTurn=ownTurns;
    ctx.op=selected.op;ctx.selectedIndex=selected.index;ctx.requestSHA=requestSHA;
    ctx.classification=selected.classification;ctx.candidateJSON=typedCandidateJSON(candidates[selected.index]);
    if(candidates[selected.index].build) { ctx.townID=candidates[selected.index].townID;ctx.buildingID=candidates[selected.index].buildingID; }
    if(candidates[selected.index].recruit) { const auto & c=candidates[selected.index];ctx.townID=c.townID;ctx.destinationArmyID=c.destinationArmyID;ctx.creatureID=c.creatureID;ctx.amount=c.amount;ctx.level=c.level; }
    preparedTyped=ctx;return selected.index;
   }
   catch(const std::exception & error)
   { logGlobal->error("DirectorTypedResponseRejected %s",error.what());typedFailure("response_rejected");return -1; }
  }
  std::this_thread::sleep_for(std::chrono::milliseconds(1));
 }
 typedFailure("response_timeout");return -1;
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


std::string CDirectorAI::typedCandidateJSON(const Candidate & c) const
{
 if(c.endTurn) return "{\"op\":\"end_turn\"}";
 if(c.build) return "{\"op\":\"build\",\"actor\":\"player_town\",\"town_id\":"+std::to_string(c.townID)+",\"building_id\":"+std::to_string(c.buildingID)+",\"category\":\""+c.category+"\",\"cost\":"+c.costJSON+"}";
 if(c.recruit) return "{\"op\":\"recruit\",\"actor\":\"player_town\",\"town_id\":"+std::to_string(c.townID)+",\"destination_army_id\":"+std::to_string(c.destinationArmyID)+",\"destination_role\":\""+(c.destinationArmyID==c.townID ? std::string("town") : std::string("garrison_hero"))+"\",\"creature_id\":"+std::to_string(c.creatureID)+",\"amount\":"+std::to_string(c.amount)+",\"level\":"+std::to_string(c.level)+",\"destination_slot\":"+std::to_string(c.nativeSlot)+",\"quantity_bucket\":\""+c.quantityBucket+"\",\"available\":"+std::to_string(c.available)+",\"affordable\":"+std::to_string(c.affordable)+",\"cost\":"+c.costJSON+"}";
 std::ostringstream out;
 out << "{\"op\":\"move\",\"kind\":" << c.kind << ",\"position\":[" << c.destination.x << ',' << c.destination.y
  << ',' << c.destination.z << "],\"next\":[" << c.next.x << ',' << c.next.y << ',' << c.next.z
  << "],\"path_cost\":" << c.cost << ",\"heuristic_score\":" << c.score << '}';
 return out.str();
}

void CDirectorAI::emitTyped(const std::string & json) const
{
 logGlobal->info("DirectorTypedEvent %s", json);
 const auto * explicitPath = std::getenv("LAB_ADV_TYPED_EVENTS");
 const auto * legacyPath = std::getenv("LAB_ADV_TRACE");
 if(!explicitPath && !legacyPath) return;
 const auto path = explicitPath ? std::string(explicitPath) : std::string(legacyPath) + ".typed.jsonl";
 std::ofstream out(path, std::ios::app | std::ios::binary);
 if(out) out << json << '\n';
}

void CDirectorAI::typedFailure(const std::string & reason) const
{
 typedProtocolFailed = true;
 logGlobal->error("DirectorTypedProtocolError %s", reason);
 traceState("typed_protocol_error");
 // Static reason identifiers only, never arbitrary broker text in JSON.
 emitTyped("{\"event\":\"typed_protocol_error\",\"player\":" + std::to_string(playerID.getNum()) +
  ",\"own_turn\":" + std::to_string(ownTurns) + "}");
}

void CDirectorAI::emitTypedBusy() const
{
 if(ownTurns<1) return;
 std::set<QueryID> queries = pendingQueries;
 for(const auto & entry : queryRequests) queries.insert(entry.second);
 std::ostringstream out;
 out << "{\"event\":\"busy_state\",\"player\":" << static_cast<int>(playerID.getNum()) << ",\"own_turn\":" << ownTurns
  << ",\"query_count\":" << queries.size() << ",\"movement_busy\":" << (movementBusy || pendingMove ? "true" : "false")
  << ",\"economy_busy\":" << (pendingEconomy ? "true" : "false")
  << ",\"battle_busy\":" << (battleBusy ? "true" : "false") << '}';
 emitTyped(out.str());
}

void CDirectorAI::emitTypedAction(const std::string & event, const TypedContext & ctx, const std::string & extra) const
{
 std::ostringstream out;
 out << "{\"event\":\"" << event << "\",\"decision_id\":";
 if(ctx.automatic) out << "null"; else out << ctx.decisionID;
 out << ",\"native_request_id\":" << ctx.nativeRequestID << ",\"player\":" << ctx.player
  << ",\"hero\":" << ctx.hero << ",\"own_turn\":" << ctx.ownTurn << ",\"op\":\"" << ctx.op
  << "\",\"pack_type\":\"" << (ctx.op == "move" ? "MoveHero" : (ctx.op=="build" ? "BuildStructure" : (ctx.op=="recruit" ? "RecruitCreatures" : "EndTurn"))) << "\",\"selected_index\":";
 if(ctx.automatic) out << "null"; else out << ctx.selectedIndex;
 out << ",\"request_sha256\":";
 if(ctx.automatic) out << "null"; else out << '"' << ctx.requestSHA << '"';
 out << ",\"candidate\":" << ctx.candidateJSON;
 if(ctx.automatic) out << ",\"automatic_reason\":\"" << ctx.automaticReason << '"';
 else out << ",\"classification\":\"" << ctx.classification << '"';
 if(ctx.op=="build") out << ",\"actor\":\"player_town\",\"town_id\":" << ctx.townID << ",\"building_id\":" << ctx.buildingID;
 if(ctx.op=="recruit") out << ",\"actor\":\"player_town\",\"town_id\":" << ctx.townID << ",\"destination_army_id\":" << ctx.destinationArmyID << ",\"creature_id\":" << ctx.creatureID << ",\"amount\":" << ctx.amount << ",\"level\":" << ctx.level;
 out << extra << '}';emitTyped(out.str());
}

// Called only after movement commitment filtering, before request publication.
void CDirectorAI::appendBuildCandidates() const
{
 if(!learnedBuildEnabled || !buildWindow.open) return;
 const BuildingID priorities[]={BuildingID::TOWN_HALL,BuildingID::CITY_HALL,BuildingID::CAPITOL,
  BuildingID::TAVERN,BuildingID::MARKETPLACE,BuildingID::BLACKSMITH,BuildingID::MAGES_GUILD_1,
  BuildingID::FORT,BuildingID::DWELL_LVL_1,BuildingID::DWELL_LVL_2,BuildingID::DWELL_LVL_3,
  BuildingID::DWELL_LVL_4,BuildingID::DWELL_LVL_5,BuildingID::DWELL_LVL_6,BuildingID::DWELL_LVL_7,
  BuildingID::CITADEL,BuildingID::CASTLE};
 std::map<std::pair<int,int>,Candidate> builds;
 for(const auto * town:cb->getTownsInfo())
 {
  if(!town || town->getOwner()!=playerID || town->id.getNum()<0) continue;
  auto offer=[&](BuildingID id)
  {
   const auto definition=town->getTown()->buildings.find(id);
   if(definition==town->getTown()->buildings.end() || definition->second->mode!=CBuilding::BUILD_NORMAL ||
      id.getNum()<0 || cb->canBuildStructure(town,id)!=EBuildingState::ALLOWED) return;
   const auto cost=town->getBuildingCost(id);
   if(!LabLearnedBuild::nonnegative(cost)) { typedFailure("negative_build_cost");return; }
   Candidate candidate{};candidate.build=true;candidate.townID=town->id.getNum();candidate.buildingID=id.getNum();
   candidate.category=(id==BuildingID::TOWN_HALL || id==BuildingID::CITY_HALL || id==BuildingID::CAPITOL) ? "income" : (id.isDwelling() ? "dwelling" : "infrastructure");
   candidate.costJSON=LabLearnedBuild::resources(cost);
   builds[{candidate.townID,candidate.buildingID}]=candidate;
  };
  for(const auto id:priorities)
  {
   offer(id);
   if(id.isDwelling() && cb->canBuildStructure(town,id)==EBuildingState::PREREQUIRES)
   {
    const auto missing=town->genBuildingRequirements(id,true).getFulfillmentCandidates([&](const BuildingID & built){return town->hasBuilt(built);});
    for(const auto prerequisite:missing) offer(prerequisite);
   }
  }
 }
 for(const auto & item:builds) candidates.push_back(item.second);
}

std::string CDirectorAI::buildTownState(int townID) const
{
 for(const auto * town:cb->getTownsInfo()) if(town && town->id.getNum()==townID && town->getOwner()==playerID)
 {
  std::ostringstream out;
  out << "{\"town_id\":" << townID << ",\"owner\":" << town->getOwner().getNum()
   << ",\"built_today\":" << town->built << ",\"buildings\":" << LabLearnedBuild::ids(town->getBuildings())
   << ",\"resources\":" << LabLearnedBuild::resources(cb->getResourceAmount()) << '}';
  return out.str();
 }
 return "null";
}

bool CDirectorAI::issuePolicyBuild()
{
 if(!learnedBuildEnabled || !preparedTyped || preparedTyped->op!="build" || pendingEconomy || outstandingTyped ||
    selectedCandidate<0 || selectedCandidate>=static_cast<int>(candidates.size()))
 { typedFailure("invalid_policy_build_state");return false; }
 const auto & chosen=candidates[selectedCandidate];
 if(!chosen.build || chosen.townID!=preparedTyped->townID || chosen.buildingID!=preparedTyped->buildingID)
 { typedFailure("build_candidate_tuple_mismatch");return false; }
 const CGTownInstance * subject=nullptr;
 for(const auto * town:cb->getTownsInfo()) if(town && town->id.getNum()==chosen.townID) subject=town;
 if(!subject || subject->getOwner()!=playerID)
 { typedFailure("selected_build_town_unowned");return false; }
 const BuildingID building(chosen.buildingID);
 const auto definition=subject->getTown()->buildings.find(building);
 if(definition==subject->getTown()->buildings.end() || definition->second->mode!=CBuilding::BUILD_NORMAL ||
    cb->canBuildStructure(subject,building)!=EBuildingState::ALLOWED ||
    LabLearnedBuild::resources(subject->getBuildingCost(building))!=chosen.costJSON)
 { typedFailure("selected_build_legality_or_cost_changed");return false; }
 preparedTyped->beforeBuildState=buildTownState(chosen.townID);
 emitTypedBusy();traceState("before_policy_build");
 if(!cb->buildBuilding(subject,building)) { typedFailure("policy_build_not_sent");return false; }
 return true;
}

void CDirectorAI::buildChanged(const CGTownInstance * town, BuildingID buildingID, int what)
{
 if(!learnedBuildEnabled || !outstandingTyped || outstandingTyped->op!="build" || !town ||
    town->getOwner()!=playerID || town->id.getNum()!=outstandingTyped->townID) return;
 if(what==1 && buildingID.getNum()==outstandingTyped->buildingID) outstandingTyped->buildResultSeen=true;
 emitTypedAction("build_changed",*outstandingTyped,",\"observed_building_id\":"+std::to_string(buildingID.getNum())+
  ",\"what\":"+std::to_string(what)+",\"state\":"+buildTownState(town->id.getNum()));
 // Observation only: never clear the tuple, synthesize ACK, or advance here.
}

// Schema6 owns creature spending. This is an actual native offer/resource/slot
// view, not a surrogate economy simulator. War machines/external dwellings excluded.
void CDirectorAI::appendRecruitCandidates() const
{
 if(!learnedRecruitEnabled || !buildWindow.open) return;
 std::map<std::tuple<int,int,int,int,int>,Candidate> offers;
 for(const auto * town:cb->getTownsInfo())
 {
  if(!town || town->getOwner()!=playerID) continue;
  const auto * army=town->getUpperArmy();
  if(!army || army->getOwner()!=playerID) continue;
  for(int level=0;level<static_cast<int>(town->creatures.size());++level)
  {
   const auto & stock=town->creatures[level];
   if(stock.first<=0 || stock.first>std::numeric_limits<int>::max()) continue;
   for(const auto id:stock.second)
   {
    const auto * definition=id.toCreature();
    if(!definition || id.getNum()<0 || definition->warMachine!=ArtifactID::NONE) continue;
    const auto slot=army->getSlotFor(id);if(!slot.validSlot()) continue;
    const int affordable=definition->maxAmount(cb->getResourceAmount()); // Same native predicate as server.
    const int limit=std::min<int>(stock.first,affordable);
    for(const int quantity:LabLearnedRecruit::quantities(limit))
    {
     const auto totalCost=definition->getFullRecruitCost()*quantity;
     if(!LabLearnedBuild::nonnegative(totalCost) || !cb->getResourceAmount().canAfford(totalCost)) continue;
     Candidate c{};c.recruit=true;c.townID=town->id.getNum();c.destinationArmyID=army->id.getNum();c.creatureID=id.getNum();c.level=level;c.amount=quantity;
     c.nativeSlot=slot.getNum();c.available=stock.first;c.affordable=affordable;
     c.quantityBucket=quantity==1 ? "one" : (quantity==limit ? "affordable_all" : "half");
     c.costJSON=LabLearnedBuild::resources(totalCost);
     offers[{c.townID,c.destinationArmyID,c.level,c.creatureID,c.amount}]=c;
    }
   }
  }
 }
 for(const auto & item:offers) candidates.push_back(item.second);
}

bool CDirectorAI::issuePolicyRecruit()
{
 if(!learnedRecruitEnabled || !buildWindow.open || !preparedTyped || preparedTyped->op!="recruit" || pendingEconomy || outstandingTyped ||
    selectedCandidate<0 || selectedCandidate>=static_cast<int>(candidates.size()))
 { typedFailure("invalid_policy_recruit_state");return false; }
 const auto chosen=candidates[selectedCandidate];
 if(!chosen.recruit || chosen.townID!=preparedTyped->townID || chosen.destinationArmyID!=preparedTyped->destinationArmyID || chosen.creatureID!=preparedTyped->creatureID || chosen.amount!=preparedTyped->amount || chosen.level!=preparedTyped->level)
 { typedFailure("recruit_candidate_tuple_mismatch");return false; }
 const CGTownInstance * town=nullptr;
 for(const auto * t:cb->getTownsInfo()) if(t && t->id.getNum()==chosen.townID && t->getOwner()==playerID) town=t;
 if(!town || chosen.level<0 || chosen.level>=static_cast<int>(town->creatures.size()))
 { typedFailure("selected_recruit_town_or_level_changed");return false; }
 const auto * army=town->getUpperArmy();const CreatureID id(chosen.creatureID);const auto * definition=id.toCreature();
 const auto & stock=town->creatures[chosen.level];
 if(!army || army->getOwner()!=playerID || army->id.getNum()!=chosen.destinationArmyID || !definition || definition->warMachine!=ArtifactID::NONE ||
    std::find(stock.second.begin(),stock.second.end(),id)==stock.second.end() || stock.first!=chosen.available || chosen.amount<=0 || chosen.amount>stock.first)
 { typedFailure("selected_recruit_stock_or_actor_changed");return false; }
 const auto slot=army->getSlotFor(id);const int affordable=definition->maxAmount(cb->getResourceAmount());
 const auto totalCost=definition->getFullRecruitCost()*chosen.amount;
 if(!slot.validSlot() || slot.getNum()!=chosen.nativeSlot || affordable!=chosen.affordable || chosen.amount>affordable ||
    !LabLearnedRecruit::quantities(std::min<int>(stock.first,affordable)).count(chosen.amount) || !LabLearnedBuild::nonnegative(totalCost) ||
    !cb->getResourceAmount().canAfford(totalCost) || LabLearnedBuild::resources(totalCost)!=chosen.costJSON)
 { typedFailure("selected_recruit_slot_or_cost_changed");return false; }
 preparedTyped->beforeStock=stock.first;preparedTyped->beforeResources=resourceTotals(cb->getResourceAmount());preparedTyped->recruitCost=resourceTotals(totalCost);
 preparedTyped->beforeArmy=armyTotals(army);preparedTyped->beforeBuildState=recruitTownState(chosen.townID);
 for(const auto & offer:town->creatures)
 {
  std::vector<int> ids;for(const auto offered:offer.second) ids.push_back(offered.getNum());
  preparedTyped->beforeRecruitStock.emplace_back(offer.first,std::move(ids));
 }
 if(const auto * visitor=town->getVisitingHero()) { preparedTyped->beforeVisitorID=visitor->id.getNum();preparedTyped->beforeVisitorArmy=armyTotals(visitor); }
 emitTypedBusy();traceState("before_policy_recruit");
 // CCallback returns void. Only the actual requestSent callback may bind this tuple.
 cb->recruitCreatures(town,army,id,chosen.amount,chosen.level);
 // No post-send liveness assertion: a real fast ACK may already have cleared it.
 return true;
}

std::string CDirectorAI::recruitTownState(int townID) const
{
 for(const auto * town:cb->getTownsInfo()) if(town && town->id.getNum()==townID && town->getOwner()==playerID)
 {
  const auto * upper=town->getUpperArmy();const auto * visitor=town->getVisitingHero();std::ostringstream out;
  out << "{\"town_id\":" << townID << ",\"owner\":" << town->getOwner().getNum() << ",\"built_today\":" << town->built
   << ",\"resources\":" << LabLearnedBuild::resources(cb->getResourceAmount()) << ",\"upper_army_id\":" << upper->id.getNum()
   << ",\"upper_army\":" << armySlotsJSON(upper) << ",\"visitor\":";
  if(visitor) out << "{\"hero_id\":" << visitor->id.getNum() << ",\"army_id\":" << visitor->id.getNum() << ",\"owner\":" << visitor->getOwner().getNum() << ",\"army\":" << armySlotsJSON(visitor) << '}';
  else out << "null";
  out << ",\"recruit_stock\":[";
  for(int level=0;level<static_cast<int>(town->creatures.size());++level)
  {
   if(level) out << ',';out << "{\"level\":" << level << ",\"available\":" << town->creatures[level].first << ",\"creature_ids\":" << LabLearnedBuild::ids(town->creatures[level].second) << '}';
  }
  out << "]}";return out.str();
 }
 return "null";
}

bool CDirectorAI::verifyRecruitApplied(const TypedContext & ctx) const
{
 for(const auto * town:cb->getTownsInfo()) if(town && town->getOwner()==playerID && town->id.getNum()==ctx.townID)
 {
  const auto * army=town->getUpperArmy();
  if(!army || army->getOwner()!=playerID || army->id.getNum()!=ctx.destinationArmyID || ctx.level<0 || ctx.level>=static_cast<int>(town->creatures.size()) || ctx.amount<=0 ||
     town->creatures[ctx.level].first!=ctx.beforeStock-ctx.amount) return false;
  auto expected=ctx.beforeArmy;expected[ctx.creatureID]+=ctx.amount;
  if(armyTotals(army)!=expected) return false;
  if(ctx.beforeRecruitStock.size()!=town->creatures.size()) return false;
  for(unsigned level=0;level<town->creatures.size();++level)
  {
   const auto & before=ctx.beforeRecruitStock[level];const auto & after=town->creatures[level];std::vector<int> ids;
   for(const auto id:after.second) ids.push_back(id.getNum());
   if(ids!=before.second || after.first!=before.first-(static_cast<int>(level)==ctx.level ? ctx.amount : 0)) return false;
  }
  const auto * visitor=town->getVisitingHero();
  if((visitor ? visitor->id.getNum() : -1)!=ctx.beforeVisitorID) return false;
  if(visitor && visitor->id.getNum()!=ctx.destinationArmyID && armyTotals(visitor)!=ctx.beforeVisitorArmy) return false;
  const auto resources=resourceTotals(cb->getResourceAmount());
  for(unsigned i=0;i<7;++i) if(resources[i]!=ctx.beforeResources[i]-ctx.recruitCost[i]) return false;
  return true;
 }
 return false;
}

bool CDirectorAI::issueFreeArmyTransferV6()
{
 if(!learnedRecruitEnabled || pendingEconomy || pendingFreeTransfer || outstandingTyped || preparedTyped) return false;
 for(const auto * town:cb->getTownsInfo())
 {
  if(!town || town->getOwner()!=playerID) continue;
  const auto * army=town->getUpperArmy();const auto * hero=town->getVisitingHero();
  if(!army || !hero || army==hero || hero->getOwner()!=playerID || army->getOwner()!=playerID || (army->needsLastStack() && army->stacksCount()<2)) continue;
  for(const auto & slot:army->Slots())
  {
   const auto id=slot.second->getCreatureID();const auto target=hero->getSlotFor(id);
   if(!target.validSlot() || slot.second->getCount()<=0 || slot.second->getCount()>std::numeric_limits<int>::max()) continue;
   TransferContext tx;tx.townID=town->id.getNum();tx.sourceArmyID=army->id.getNum();tx.targetArmyID=hero->id.getNum();tx.creatureID=id.getNum();tx.amount=slot.second->getCount();tx.fromSlot=slot.first.getNum();tx.toSlot=target.getNum();
   tx.expectedWhat=army->getCreature(slot.first)==hero->getCreature(target) ? 2 : 1;
   tx.sourceBefore=armyTotals(army);tx.targetBefore=armyTotals(hero);tx.resources=resourceTotals(cb->getResourceAmount());tx.beforeState=recruitTownState(tx.townID);
   tx.fingerprint=tx.beforeState+"/"+std::to_string(tx.fromSlot)+"/"+std::to_string(tx.toSlot);
   if(!attemptedFreeTransferStates.insert(tx.fingerprint).second) continue;
   pendingFreeTransfer=tx;pendingEconomy=true;economyRequest=-1;
   traceState("before_army_transfer");cb->mergeOrSwapStacks(army,hero,slot.first,target);return true;
  }
 }
 return false;
}

bool CDirectorAI::verifyFreeTransferApplied(const TransferContext & ctx) const
{
 for(const auto * town:cb->getTownsInfo()) if(town && town->getOwner()==playerID && town->id.getNum()==ctx.townID)
 {
  const auto * source=town->getUpperArmy();const auto * target=town->getVisitingHero();
  if(!source || !target || source->id.getNum()!=ctx.sourceArmyID || target->id.getNum()!=ctx.targetArmyID || source->getOwner()!=playerID || target->getOwner()!=playerID || resourceTotals(cb->getResourceAmount())!=ctx.resources) return false;
  auto expectedSource=ctx.sourceBefore;auto expectedTarget=ctx.targetBefore;
  if(expectedSource[ctx.creatureID]<ctx.amount || ctx.amount<=0) return false;
  expectedSource[ctx.creatureID]-=ctx.amount;if(expectedSource[ctx.creatureID]==0) expectedSource.erase(ctx.creatureID);
  expectedTarget[ctx.creatureID]+=ctx.amount;
  return armyTotals(source)==expectedSource && armyTotals(target)==expectedTarget;
 }
 return false;
}

bool CDirectorAI::exportCreatureCatalog()
{
 // This is the actual public runtime registry, not a guessed core-ID range.
 std::map<int,std::string> entries;std::set<std::string> keys;
 for(const auto & creature:LIBRARY->creh->objects)
 {
  if(!creature) continue;
  const auto id=creature->getIndex();const auto key=creature->getJsonKey();
  if(id<0 || key.empty() || !entries.emplace(id,key).second || !keys.insert(key).second)
  { typedFailure("invalid_runtime_creature_catalog");return false; }
 }
 if(entries.empty()) { typedFailure("empty_runtime_creature_catalog");return false; }
 std::ostringstream out;out << "{\"schema\":\"strategy-runtime-creature-catalog-v1\",\"entries\":[";bool first=true;
 for(const auto & item:entries)
 {
  if(!first) out << ',';first=false;
  out << "{\"creature_id\":" << item.first << ",\"canonical_key\":" << LabLearnedRecruit::jsonString(item.second) << '}';
 }
 out << "]}\n";const auto bytes=out.str();creatureCatalogSHA=LabTypedPolicy::sha256(bytes);
 const auto * agent=std::getenv("LAB_ADV_AGENT_DIR");
 if(!agent) { typedFailure("creature_catalog_missing_agent_directory");return false; }
 const auto path=std::string(agent)+"/creature-catalog.json";
 std::ifstream prior(path,std::ios::binary);
 if(prior)
 {
  const std::string existing((std::istreambuf_iterator<char>(prior)),std::istreambuf_iterator<char>());
  if(existing!=bytes) { typedFailure("creature_catalog_existing_bytes_differ");return false; }
 }
 else
 {
  std::ofstream file(path+".tmp",std::ios::binary);file << bytes;file.close();
  if(!file || std::rename((path+".tmp").c_str(),path.c_str())!=0)
  { typedFailure("creature_catalog_publish_failed");return false; }
 }
 const auto json=bytes.substr(0,bytes.size()-1);
 logGlobal->info("DirectorCreatureCatalog sha256=%s json=%s",creatureCatalogSHA,json);
 // Actual capsule/source/bin/load binding is certified externally against this
 // raw SHA and log mirror; do not trust an ENV-supplied capsule identity as proof.
 return true;
}
