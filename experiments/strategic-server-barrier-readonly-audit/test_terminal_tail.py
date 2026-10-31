import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'strategic-policy-v2'))
from audit_supply_raw import audit_terminal_tail

class TerminalTailTest(unittest.TestCase):
    def setUp(self):
        self.terminal=dict(event='defeat',day=46,player=0,heroes=[],towns=[],gold=40)
    def records(self,event):
        tail=copy.deepcopy(self.terminal);tail['event']=event
        return [(1,self.terminal),(2,tail)]
    def test_legal_ready(self):
        self.assertEqual(audit_terminal_tail(self.records('native_battle_ready'))['count'],1)
    def test_terminal_only(self):
        self.assertEqual(audit_terminal_tail([(1,self.terminal)])['count'],0)
    def test_before_move_rejected(self):
        with self.assertRaises(AssertionError):audit_terminal_tail(self.records('before_move'))
    def test_unknown_rejected(self):
        with self.assertRaises(AssertionError):audit_terminal_tail(self.records('future_event'))
    def test_ack_rejected(self):
        with self.assertRaises(AssertionError):audit_terminal_tail(self.records('move_applied'))
    def test_state_change_rejected(self):
        rows=self.records('native_battle_ready');rows[1][1]['gold']=41
        with self.assertRaises(AssertionError):audit_terminal_tail(rows)
    def test_no_terminal_rejected(self):
        with self.assertRaises(AssertionError):audit_terminal_tail([(1,dict(event='turn_end'))])
    def test_duplicate_terminal_rejected(self):
        with self.assertRaises(AssertionError):audit_terminal_tail(self.records('defeat'))

if __name__=='__main__':unittest.main()
