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
	bool found = false;
	candidates.clear();
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
			InfoAboutHero enemy;
			if(!cb->getHeroInfo(obj, enemy, hero))
			{
				audit(obj->visitablePos(), 0, "info_unavailable", -1);
				continue;
			}
			// Use the same approximate, disguise-aware army descriptor exposed to a player.
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
	if(found && !std::getenv("LAB_ADV_AGENT_DIR"))
		return true;
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

	if(found && std::getenv("LAB_ADV_AGENT_DIR"))
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
		const int selected = chooseExternalCandidate(hero);
		if(selected < 0 || selected >= static_cast<int>(candidates.size()))
		{
			logGlobal->error("DirectorAI: external policy failed for hero %d", hero->id.getNum());
			return false;
		}
		selectedCandidate = selected;
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
	traceDecision(hero, destination, step);
	cb->moveHero(hero, hero->convertFromVisitablePos(step), false, EPathfindingLayer::LAND);
	return true;
}

void CDirectorAI::yourTurn(QueryID queryID)
{
	pendingMove = false;
	pendingHero = ObjectInstanceID();
	turnActive = true;
	endingTurn = false;
	battleBusy = false;
	blockedHeroes.clear();
	committedTargets.clear();
	recruitedThisTurn.clear();
	++ownTurns;
	traceState("turn_start");
	if(!savedInitial)
	{
		savedInitial = true;
		cb->save("Saves/director-v5-initial", false);
	}
	movesThisTurn = 0;
	if(queryID != QueryID(-1))
	{
		pendingQueries.insert(queryID);
		cb->selectionMade(0, queryID);
	}
	advanceTurn();
}

void CDirectorAI::advanceTurn()
{
	if(!turnActive || endingTurn || pendingMove || pendingEconomy || battleBusy || !pendingQueries.empty())
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
	if(auto reply = dynamic_cast<const QueryReply *>(pack))
		queryRequests[requestID] = reply->qid;
	if(pendingEconomy && (dynamic_cast<const BuildStructure *>(pack) ||
		dynamic_cast<const RecruitCreatures *>(pack) || dynamic_cast<const ArrangeStacks *>(pack) ||
		dynamic_cast<const HireHero *>(pack)))
		economyRequest = requestID;
}

void CDirectorAI::queryResolved(QueryID queryID)
{
	pendingQueries.erase(queryID);
	advanceTurn();
}

void CDirectorAI::playerBlocked(int reason, bool start)
{
	if(reason == PlayerBlocked::UPCOMING_BATTLE && start)
		battleBusy = true;
}

void CDirectorAI::battleEnded()
{
	battleBusy = false;
	advanceTurn();
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
			BuildingID::DWELL_LVL_2, BuildingID::DWELL_LVL_3, BuildingID::CITADEL, BuildingID::CASTLE};
		for(const auto building : priorities)
		{
			if(cb->canBuildStructure(town, building) != EBuildingState::ALLOWED)
				continue;
			traceState("before_build");
			logGlobal->info("DirectorAI: build town=%d building=%d", town->id.getNum(), building.getNum());
			pendingEconomy = true;
			cb->buildBuilding(town, building);
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
		out << "{\"kind\":" << c.kind << ",\"position\":[" << c.destination.x << ',' << c.destination.y
			<< ',' << c.destination.z << "],\"next\":[" << c.next.x << ',' << c.next.y << ',' << c.next.z
			<< "],\"path_cost\":" << c.cost << ",\"heuristic_score\":" << c.score << '}';
	}
	out << "]}\n";
}

int CDirectorAI::chooseExternalCandidate(const CGHeroInstance * hero) const
{
	const auto * directory = std::getenv("LAB_ADV_AGENT_DIR");
	if(!directory)
		return -1;
	char suffix[32];
	std::snprintf(suffix, sizeof(suffix), "%08u.json", ++externalDecisionSerial);
	const std::string request = std::string(directory) + "/request-" + suffix;
	const std::string response = std::string(directory) + "/action-" + suffix;
	{
		std::ofstream out(request + ".tmp");
		if(!out)
			return -1;
		out << "{\"schema\":\"strategy-candidates-v2\",\"request_id\":" << externalDecisionSerial
			<< ",\"player\":" << static_cast<int>(playerID.getNum())
			<< ",\"day\":" << cb->getCalendar().getCurrentDay() << ",\"hero\":" << hero->id.getNum()
			<< ",\"from\":[" << hero->visitablePos().x << ',' << hero->visitablePos().y << ',' << hero->visitablePos().z
			<< "],\"gold\":" << cb->getResourceAmount(GameResID::GOLD)
			<< ",\"wood\":" << cb->getResourceAmount(GameResID::WOOD)
			<< ",\"ore\":" << cb->getResourceAmount(GameResID::ORE)
			<< ",\"own_army_value\":" << ArmyDescriptor(hero, true).getStrength()
			<< ",\"movement\":" << hero->movementPointsRemaining() << ",\"candidates\":[";
		bool first = true;
		for(const auto & c : candidates)
		{
			if(!first) out << ',';
			first = false;
			out << "{\"kind\":" << c.kind << ",\"position\":[" << c.destination.x << ',' << c.destination.y << ',' << c.destination.z
				<< "],\"next\":[" << c.next.x << ',' << c.next.y << ',' << c.next.z
				<< "],\"path_cost\":" << c.cost << ",\"heuristic_score\":" << c.score << '}';
		}
		out << "]}\n";
	}
	if(std::rename((request + ".tmp").c_str(), request.c_str()) != 0)
		return -1;
	const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(30);
	while(std::chrono::steady_clock::now() < deadline)
	{
		std::ifstream in(response);
		if(in)
		{
			int index = -1;
			if(!(in >> index))
				return -1;
			std::string extra;
			if(in >> extra)
				return -1;
			return index >= 0 && index < static_cast<int>(candidates.size()) ? index : -1;
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(1));
	}
	return -1;
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
