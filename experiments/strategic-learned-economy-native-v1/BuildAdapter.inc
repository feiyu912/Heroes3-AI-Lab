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
