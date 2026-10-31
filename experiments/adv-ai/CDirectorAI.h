/*
 * CDirectorAI.h, part of the Heroes3-AI-Lab adventure layer.
 *
 * First custom adventure-map policy. It delegates every battle to a native battle AI
 * (BattleAI) and only decides strategy: which hero moves and where.
 *
 * The policy is deliberately simple and deterministic so that it can serve as a
 * reproducible baseline before any learned strategic model is attached:
 *   - pick the owned hero with the most remaining movement points
 *   - advance toward the nearest visible enemy hero, else the nearest visible enemy town,
 *     else a deterministic scouting waypoint
 *
 * This is a baseline, not a trained policy, and must not be reported as a learned strategy.
 */
#pragma once

#include "../../lib/callback/CAdventureAI.h"
#include "../../lib/pathfinder/CGPathNode.h"
#include "../../lib/pathfinder/PathfinderCache.h"
#include "battle/AutocombatPreferences.h"

struct HeroMoveDetails;

class CDirectorAI : public CAdventureAI
{
public:
	void initGameInterface(std::shared_ptr<Environment> ENV, std::shared_ptr<CCallback> CB, AutocombatPreferences ap) override;
	void initBattleInterface(std::shared_ptr<Environment> ENV, std::shared_ptr<CBattleCallback> CB, AutocombatPreferences ap) override;
	void yourTurn(QueryID queryID) override;
	void heroGotLevel(const CGHeroInstance *hero, PrimarySkill pskill, std::vector<SecondarySkill> &skills, QueryID queryID) override;
	void commanderGotLevel (const CCommanderInstance * commander, std::vector<ui32> skills, QueryID queryID) override;
	void showBlockingDialog(const std::string &text, const std::vector<Component> &components, QueryID askID, const int soundID, bool selection, bool cancel, bool safeToAutoaccept) override;
	void showTeleportDialog(const CGHeroInstance * hero, TeleportChannelID channel, TTeleportExitsList exits, bool impassable, QueryID askID) override;
	void showGarrisonDialog(const CArmedInstance * up, const CGHeroInstance * down, bool removableUnits, QueryID queryID, const MetaString & customTitle) override;
	void showMapObjectSelectDialog(QueryID askID, const Component & icon, const MetaString & title, const MetaString & description, const std::vector<ObjectInstanceID> & objects) override;
	std::string getBattleAIName() const override;
	std::optional<BattleAction> makeSurrenderRetreatDecision(const BattleID & battleID, const BattleStateInfoForRetreat & battleState) override;
	void heroMoved(const TryMoveHero & details, bool verbose = true) override;
	void requestRealized(PackageApplied * pa) override;
	void requestSent(const CPackForServer * pack, int requestID) override;
	void queryResolved(QueryID queryID) override;
	void playerBlocked(int reason, bool start) override;
	void battleEnded() override;
	void gameOver(PlayerColor player, const EVictoryLossCheckResult & result) override;

private:
	static constexpr int MAX_MOVES_PER_TURN = 128;

	std::shared_ptr<CCallback> cb;
	std::unique_ptr<PathfinderOptions> pathfinderOptions;
	std::unique_ptr<PathfinderCache> pathfinder;
	bool turnActive = false;
	bool pendingMove = false;
	bool battleBusy = false;
	bool movementBusy = false;
	bool endingTurn = false;
	std::set<QueryID> pendingQueries;
	std::map<int, QueryID> queryRequests;
	bool pendingEconomy = false;
	int economyRequest = -1;
	bool savedInitial = false;
	int ownTurns = 0;
	std::set<std::pair<int, int>> recruitedThisTurn;
	struct Candidate
	{
		int3 destination;
		int3 next;
		int kind;
		double cost;
		double score;
	};
	mutable std::vector<Candidate> candidates;
	mutable int selectedCandidate = -1;
	mutable unsigned externalDecisionSerial = 0;
	mutable std::map<int, std::pair<int3, int>> committedTargets;
	mutable std::vector<std::pair<int3, double>> visibleThreats;
	std::set<int> blockedHeroes;
	int movesThisTurn = 0;
	ObjectInstanceID pendingHero;
	int3 lastStep = int3(-1, -1, -1);

	bool issueMove();
	bool issueEconomy();
	void traceState(const std::string & event) const;
	void traceDecision(const CGHeroInstance * hero, const int3 & destination, const int3 & step) const;
	int chooseExternalCandidate(const CGHeroInstance * hero) const;
	void advanceTurn();
	void finishTurn();
	const CGHeroInstance * pickHero(std::vector<const CGHeroInstance *> & heroes) const;
	bool findTarget(const CGHeroInstance * hero, int3 & destination, std::string & reason) const;
};

