"""Scripted coordinate-clearance hypothesis on existing legal candidates, never an expert label."""
def choose(request,baseline_index,release_event):
    candidates=request['candidates'];baseline=candidates[baseline_index]
    result=dict(index=baseline_index,overridden=False,method='scripted_visible_coordinate_proxy',reason='no_bounded_release')
    if release_event is None:return result
    assert all(release_event[k]==request[k] for k in ['hero','own_turn','day','from'])
    assert release_event['decision_id']==request['request_id']
    if baseline['op']!='move':result['reason']='preserve_policy_stop';return result
    own=request['own_army_value'];origin=request['from']
    threats=[t for t in request['visible_threats'] if t['position'][2]==origin[2] and own>0 and t['approx_army_value']>=1.5*own
             and max(abs(t['position'][0]-origin[0]),abs(t['position'][1]-origin[1]))<=12]
    if not threats:result['reason']='no_visible_pressure';return result
    def clearance(pos):return min(max(abs(pos[0]-t['position'][0]),abs(pos[1]-t['position'][1])) for t in threats)
    here=clearance(origin);old=clearance(baseline['next'])
    # Exclude primary military destinations. Other paths can still encounter
    # guards: no assertion of safety, enemy reachability or casualty prediction.
    eligible=[i for i,c in enumerate(candidates) if c['op']=='move' and c['kind'] not in (0,1)
              and c['next'][2]==origin[2] and clearance(c['next'])>max(here,old)]
    result.update(origin_clearance=here,baseline_clearance=old,eligible_alternatives=len(eligible))
    if not eligible:result['reason']='no_existing_nonmilitary_step_improves_clearance';return result
    index=max(eligible,key=lambda i:(clearance(candidates[i]['next']),candidates[i]['kind']==4,
                                   -candidates[i]['path_cost'],candidates[i]['heuristic_score'],-i))
    result.update(index=index,overridden=index!=baseline_index,reason='strict_existing_step_clearance_increase',
                  selected_clearance=clearance(candidates[index]['next']))
    return result
