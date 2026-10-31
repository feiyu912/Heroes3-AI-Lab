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
#include "TypedPolicyProtocol.h"

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
 void buildChanged(const CGTownInstance * town, BuildingID buildingID, int what) override;
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
		bool endTurn = false;
  bool build = false; int townID = -1; int buildingID = -1;
  bool recruit = false; int destinationArmyID = -1; int creatureID = -1; int amount = 0; int level = -1;
  int nativeSlot = -1; int available = 0; int affordable = 0; std::string quantityBucket;
  std::string category, costJSON;
	};
	mutable std::vector<Candidate> candidates;
	mutable int selectedCandidate = -1;
	mutable unsigned externalDecisionSerial = 0;
	mutable std::map<int, std::pair<int3, int>> committedTargets;
	mutable std::vector<std::pair<int3, double>> visibleThreats;
	bool threatReplanEnabled = false;
	mutable std::set<int> threatReplanUsed;
	std::set<int> blockedHeroes;
	int movesThisTurn = 0;
	ObjectInstanceID pendingHero;
	int3 lastStep = int3(-1, -1, -1);


 struct TypedContext
 {
  bool automatic = false;bool moveResultSeen = false;bool buildResultSeen = false;
  int townID = -1;int buildingID = -1;std::string beforeBuildState;
  int destinationArmyID=-1;int creatureID=-1;int amount=0;int level=-1;int beforeStock=0;
  std::array<std::int64_t,7> beforeResources{},recruitCost{};
  std::map<int,std::int64_t> beforeArmy;
  std::vector<std::pair<std::int64_t,std::vector<int>>> beforeRecruitStock;
  int beforeVisitorID=-1;std::map<int,std::int64_t> beforeVisitorArmy;
  int3 objectStep = int3(-1,-1,-1);
  int decisionID = -1;int nativeRequestID = -1;int player = 0;int hero = 0;int ownTurn = 0;int selectedIndex = -1;
  std::string op, requestSHA, candidateJSON, classification, automaticReason;
 };
 bool learnedBuildEnabled = false;
 bool learnedRecruitEnabled = false;
 std::string creatureCatalogSHA;
 bool exportCreatureCatalog();
 struct TransferContext
 {
  int townID=-1,sourceArmyID=-1,targetArmyID=-1,creatureID=-1,amount=0,fromSlot=-1,toSlot=-1,nativeRequestID=-1,expectedWhat=-1;
  std::array<std::int64_t,7> resources{};
  std::map<int,std::int64_t> sourceBefore,targetBefore;
  std::string fingerprint,beforeState;
 };
 std::optional<TransferContext> pendingFreeTransfer;
 std::set<std::string> attemptedFreeTransferStates;
 LabLearnedBuild::Window buildWindow;
 void appendBuildCandidates() const;
 std::string buildTownState(int townID) const;
 bool issuePolicyBuild();
 void appendRecruitCandidates() const;
 bool issuePolicyRecruit();
 std::string recruitTownState(int townID) const;
 bool verifyRecruitApplied(const TypedContext & ctx) const;
 bool verifyFreeTransferApplied(const TransferContext & ctx) const;
 mutable std::optional<TypedContext> preparedTyped;
 std::optional<TypedContext> outstandingTyped;
 mutable bool typedProtocolFailed = false;
 std::string typedCandidateJSON(const Candidate & candidate) const;
 void emitTyped(const std::string & json) const;
 void emitTypedBusy() const;
 void emitTypedAction(const std::string & event, const TypedContext & ctx, const std::string & extra = "") const;
 void typedFailure(const std::string & reason) const;
 bool issueMove();
	bool issueEconomy();
	bool issueFreeArmyTransfer();
 bool issueFreeArmyTransferV6();
	void traceState(const std::string & event) const;
	void traceDecision(const CGHeroInstance * hero, const int3 & destination, const int3 & step) const;
	int chooseExternalCandidate(const CGHeroInstance * hero) const;
	void advanceTurn();
	void finishTurn();
	const CGHeroInstance * pickHero(std::vector<const CGHeroInstance *> & heroes) const;
	bool findTarget(const CGHeroInstance * hero, int3 & destination, std::string & reason) const;
};

