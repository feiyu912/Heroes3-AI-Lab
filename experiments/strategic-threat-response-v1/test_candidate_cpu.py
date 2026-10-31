"""Review/source equivalence and commit-state counterexamples; no compiler/game."""
from pathlib import Path
import hashlib,json,unittest
import threat_contract
from prepare_candidate import expected_candidate,ADDITION
from test_contract import request

HERE=Path(__file__).resolve().parent

def native_expression(position,own,threats):
    return any(t['position'][2]==position[2]
        and max(abs(t['position'][0]-position[0]),abs(t['position'][1]-position[1]))<=12
        and t['approx_army_value']>=1.5*max(1.0,float(own))for t in threats)

def branch(existing,pressure,candidates):
    """Pure state sketch of only the source branch, not native execution."""
    events=[]
    if pressure and existing is not None:
        existing=None;events.append('threat_commit_released')
    if existing is not None and existing in candidates:candidates=[existing]
    return existing,candidates,events

class CandidateTest(unittest.TestCase):
    def test_exact_single_insertion(self):
        base=(HERE/'baseline-CDirectorAI.cpp').read_text();candidate=(HERE/'candidate-CDirectorAI.cpp').read_text()
        self.assertEqual(candidate,expected_candidate(base))
        self.assertEqual(candidate.replace(ADDITION,''),base)
        self.assertEqual(candidate.count('traceState("threat_commit_released")'),1)
    def test_threshold_matches_contract_grid(self):
        self.assertEqual((threat_contract.RATIO,threat_contract.GRID_RADIUS),(1.5,12))
        for own in (0,1,100):
            for enemy in (0,1,1.49,1.5,149,150,151):
                for dx in (-13,-12,0,12,13):
                    for dz in (0,1):
                        r=request();r['own_army_value']=own;r['visible_threats']=[dict(position=[5+dx,5,dz],approx_army_value=enemy)]
                        self.assertEqual(threat_contract.release_gate(r)['keep_full_native_candidates'],
                            native_expression(r['from'],own,r['visible_threats']))
    def test_no_commit_no_release_event(self):
        self.assertEqual(branch(None,True,[1,2,3]),(None,[1,2,3],[]))
    def test_pressure_erases_existing(self):
        self.assertEqual(branch(2,True,[1,2,3]),(None,[1,2,3],['threat_commit_released']))
    def test_no_pressure_preserves_old_collapse(self):
        self.assertEqual(branch(2,False,[1,2,3]),(2,[2],[]))
    def test_no_pressure_missing_destination_preserves_original_list(self):
        self.assertEqual(branch(9,False,[1,2,3]),(9,[1,2,3],[]))
    def test_pressure_single_list_no_invention(self):
        self.assertEqual(branch(2,True,[2]),(None,[2],['threat_commit_released']))
    def test_repeated_pressure_can_release_every_selection(self):
        _,options,events=branch(1,True,[1,2]);self.assertEqual(len(options),2)
        # Native selection subsequently re-commits; next request can release it.
        _,options2,events2=branch(2,True,[1,2])
        self.assertEqual(events+events2,['threat_commit_released']*2)
        self.assertEqual(len(options2),2)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(CandidateTest)
    result=unittest.TextTestRunner().run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    out=HERE/'CANDIDATE_CPU_RESULT.json'
    assert not out.exists(),'Do not overwrite review results'
    files=['baseline-CDirectorAI.cpp','candidate-CDirectorAI.cpp','candidate.diff','CANDIDATE_MANIFEST.json',
           'prepare_candidate.py','test_candidate_cpu.py','threat_contract.py']
    out.write_text(json.dumps(dict(passed=True,tests=result.testsRun,threshold_cases=3*7*5*2,
        compiled=False,native_runs=0,pool_used=False,
        scope='Source identity and CPU branch model only; not C++ compilation or native legality verification',
        sources={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest()for name in files}),indent=2))
