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
				candidates.assign(1, committed);
			}
		}
		Candidate stop{};stop.endTurn=true;candidates.push_back(stop);
		const int selected = chooseExternalCandidate(hero);
		if(selected < 0 || selected >= static_cast<int>(candidates.size()))
		{
			logGlobal->error("DirectorAI: external policy failed for hero %d", hero->id.getNum());
			return false;
		}
		selectedCandidate = selected;
		if(candidates[selected].endTurn) { reason="typed_end_turn";return true; }
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
 turnActive=true;endingTurn=false;blockedHeroes.clear();committedTargets.clear();recruitedThisTurn.clear();
 ++ownTurns;traceState("turn_start");
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
 if(issueEconomy()) return;
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
 if(!move && !end) return;
 if(!outstandingTyped || outstandingTyped->nativeRequestID!=static_cast<int>(pa->requestID) ||
    outstandingTyped->op!=(move ? "move" : "end_turn")) { typedFailure("unmatched_typed_ack");return; }
 const auto ctx=*outstandingTyped; // Save the old turn, never substitute the live ownTurns.
 emitTypedAction("package_applied",ctx,std::string(",\"source\":\"client\",\"package\":\"PackageApplied\",\"success\":")+(pa->result ? "true" : "false"));
 outstandingTyped.reset(); // Only this exact native request/op ACK can clear the tuple.
 if(move)
 {
  pendingMove=false;traceState(pa->result ? "move_applied" : "move_failed");
  if(!pa->result) blockedHeroes.insert(ctx.hero);
 }
 else if(ctx.ownTurn==ownTurns)
 {
  endingTurn=false;if(pa->result) turnActive=false;
 }
 if(!pa->result) typedFailure("native_action_ack_failed");
 advanceTurn(); // A late old EndTurn ACK resumes the already-started new turn safely.
}


void CDirectorAI::requestSent(const CPackForServer * pack, int requestID)
{
 if(auto reply=dynamic_cast<const QueryReply *>(pack)) queryRequests[requestID]=reply->qid;
 if(pendingEconomy && (dynamic_cast<const BuildStructure *>(pack) || dynamic_cast<const RecruitCreatures *>(pack) ||
    dynamic_cast<const ArrangeStacks *>(pack) || dynamic_cast<const HireHero *>(pack))) economyRequest=requestID;
 const bool move=dynamic_cast<const MoveHero *>(pack)!=nullptr;
 const bool end=dynamic_cast<const EndTurn *>(pack)!=nullptr;
 if(!move && !end) return;
 if(requestID<1 || !preparedTyped || outstandingTyped || preparedTyped->ownTurn!=ownTurns ||
    preparedTyped->op!=(move ? "move" : "end_turn")) { typedFailure("unbound_native_request");return; }
 outstandingTyped=*preparedTyped;outstandingTyped->nativeRequestID=requestID;preparedTyped.reset();
 emitTypedAction("native_action_sent",*outstandingTyped);
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
		const BuildingID priorities[] = {BuildingID::TOWN_HALL, BuildingID::CITY_HALL,
			BuildingID::CAPITOL, BuildingID::TAVERN, BuildingID::MARKETPLACE,
			BuildingID::BLACKSMITH, BuildingID::MAGES_GUILD_1, BuildingID::FORT, BuildingID::DWELL_LVL_1,
			BuildingID::DWELL_LVL_2, BuildingID::DWELL_LVL_3, BuildingID::DWELL_LVL_4,
			BuildingID::DWELL_LVL_5, BuildingID::DWELL_LVL_6, BuildingID::DWELL_LVL_7,
			BuildingID::CITADEL, BuildingID::CASTLE};
		for(const auto building : priorities)
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
 out << "{\"schema\":\"strategy-candidates-v4\",\"request_id\":" << externalDecisionSerial
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
 out << "],\"own_towns\":[";first=true;
 for(const auto * town : cb->getTownsInfo())
 {
  if(!first) out << ',';first=false;const int3 pos=town->visitablePos();
  out << "{\"position\":[" << pos.x << ',' << pos.y << ',' << pos.z
   << "],\"army_value\":" << ArmyDescriptor(town->getUpperArmy(),true).getStrength() << '}';
 }
 out << "],\"candidates\":[";first=true;std::vector<std::string> operations;
 for(const auto & c : candidates)
 {
  if(!first) out << ',';first=false;out << typedCandidateJSON(c);
  operations.push_back(c.endTurn ? "end_turn" : "move");
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
       hero->id.getNum(),ownTurns,requestSHA,operations);
    TypedContext ctx;ctx.automatic=false;ctx.decisionID=static_cast<int>(externalDecisionSerial);
    ctx.player=playerID.getNum();ctx.hero=hero->id.getNum();ctx.ownTurn=ownTurns;
    ctx.op=selected.op;ctx.selectedIndex=selected.index;ctx.requestSHA=requestSHA;
    ctx.classification=selected.classification;ctx.candidateJSON=typedCandidateJSON(candidates[selected.index]);
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
  << "\",\"pack_type\":\"" << (ctx.op == "move" ? "MoveHero" : "EndTurn") << "\",\"selected_index\":";
 if(ctx.automatic) out << "null"; else out << ctx.selectedIndex;
 out << ",\"request_sha256\":";
 if(ctx.automatic) out << "null"; else out << '"' << ctx.requestSHA << '"';
 out << ",\"candidate\":" << ctx.candidateJSON;
 if(ctx.automatic) out << ",\"automatic_reason\":\"" << ctx.automaticReason << '"';
 else out << ",\"classification\":\"" << ctx.classification << '"';
 out << extra << '}';emitTyped(out.str());
}
