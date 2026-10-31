import copy
import unittest
from threat_contract import release_gate,choose_existing_retreat_proxy,validate_v3,validate_v4_action,ExecutionContract

def request():
    return dict(schema='strategy-candidates-v3',request_id=1,player=0,day=1,hero=0,gold=0,wood=0,ore=0,
        own_army_value=100,movement=300,**{'from':[5,5,0]},
        visible_threats=[dict(position=[7,5,0],approx_army_value=200)],
        own_towns=[dict(position=[2,5,0],army_value=50)],
        candidates=[dict(kind=5,position=[9,5,0],next=[6,5,0],path_cost=.5,heuristic_score=2),
                    dict(kind=4,position=[2,5,0],next=[4,5,0],path_cost=.7,heuristic_score=1)])

class ContractTest(unittest.TestCase):
    def test_active_release(self):self.assertTrue(release_gate(request())['keep_full_native_candidates'])
    def test_no_visible_enemy(self):
        r=request();r['visible_threats']=[]
        self.assertFalse(release_gate(r)['keep_full_native_candidates'])
        self.assertEqual(choose_existing_retreat_proxy(r,0)[0],0)
    def test_missing_visibility_rejected(self):
        r=request();del r['visible_threats']
        with self.assertRaises(ValueError):release_gate(r)
    def test_hidden_fields_rejected(self):
        r=request();r['future_enemy_rng']=42
        with self.assertRaises(ValueError):release_gate(r)
    def test_other_level_not_near(self):
        r=request();r['visible_threats'][0]['position'][2]=1
        self.assertFalse(release_gate(r)['keep_full_native_candidates'])
    def test_legal_proxy_move(self):self.assertEqual(choose_existing_retreat_proxy(request(),0)[0],1)
    def test_single_candidate_no_invention(self):
        r=request();r['candidates']=r['candidates'][:1]
        self.assertEqual(choose_existing_retreat_proxy(r,0)[0],0)
    def test_does_not_mutate_input(self):
        r=request();before=copy.deepcopy(r);choose_existing_retreat_proxy(r,0);self.assertEqual(r,before)
    def test_siege_not_retreat(self):
        r=request();r['candidates'][1]['kind']=1
        self.assertEqual(choose_existing_retreat_proxy(r,0)[0],0)
    def test_v3_hold_rejected(self):
        r=request();r['candidates'].append(dict(op='end_turn',scope='player'))
        with self.assertRaises(ValueError):validate_v3(r)
    def test_v4_real_endturn(self):
        self.assertEqual(validate_v4_action(dict(op='end_turn',scope='player'),from_pos=[5,5,0],own_hero_count=1),'EndTurn')
    def test_endturn_coordinates_rejected(self):
        with self.assertRaises(ValueError):validate_v4_action(dict(op='end_turn',scope='player',next=[5,5,0]),from_pos=[5,5,0],own_hero_count=1)
    def test_multihero_hold_rejected(self):
        with self.assertRaises(ValueError):validate_v4_action(dict(op='end_turn',scope='player'),from_pos=[5,5,0],own_hero_count=2)
    def test_same_tile_visit_is_not_hold(self):
        c=dict(request()['candidates'][0],op='move',position=[5,5,0],next=[5,5,0])
        self.assertEqual(validate_v4_action(c,from_pos=[5,5,0],own_hero_count=1),'MoveHero')
    def test_hold_needs_actual_endturn_ack(self):
        e=ExecutionContract();e.sent(1,20,'EndTurn')
        with self.assertRaises(ValueError):e.confirm(20,'MoveHero',server_received=True,server_applied=True,ack_success=True)
        with self.assertRaises(ValueError):e.confirm(21,'EndTurn',server_received=True,server_applied=True,ack_success=True)
        e.confirm(20,'EndTurn',server_received=True,server_applied=True,ack_success=True)
        self.assertTrue(e.settled())
    def test_success_ack_not_execution(self):
        e=ExecutionContract();e.sent(1,20,'EndTurn')
        with self.assertRaises(ValueError):e.confirm(20,'EndTurn',server_received=True,server_applied=False,ack_success=True)
    def test_gameover_not_confirmation(self):
        e=ExecutionContract();e.sent(1,20,'MoveHero');e.game_over();self.assertFalse(e.settled())
        with self.assertRaises(ValueError):e.sent(2,21,'MoveHero')
    def test_no_second_pending_decision(self):
        e=ExecutionContract();e.sent(1,20,'EndTurn')
        with self.assertRaises(ValueError):e.sent(2,21,'MoveHero')
    def test_nan_rejected(self):
        r=request();r['visible_threats'][0]['approx_army_value']=float('nan')
        with self.assertRaises(ValueError):release_gate(r)

if __name__=='__main__':unittest.main()
