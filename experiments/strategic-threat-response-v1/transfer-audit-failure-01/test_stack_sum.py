from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'strategic-policy-v2'))
from audit_supply_raw import army

def conserved(hb,ha,tb,ta):
    hb,ha,tb,ta=[army(dict(army=a))for a in (hb,ha,tb,ta)]
    gain=ha-hb;loss=tb-ta
    return bool(gain)and gain==loss and ha==hb+gain and tb==ta+loss

class StackSumTest(unittest.TestCase):
    def test_multiple_same_creature(self):self.assertEqual(army(dict(army=[[2,6],[2,4],[2,6]]))[2],16)
    def test_reordering(self):self.assertEqual(army(dict(army=[[2,6],[2,4],[2,8]])),army(dict(army=[[2,8],[2,6],[2,4]])))
    def test_split_merge(self):self.assertEqual(army(dict(army=[[2,16]])),army(dict(army=[[2,6],[2,4],[2,6]])))
    def test_multiple_species(self):self.assertEqual(army(dict(army=[[2,6],[0,4],[2,10],[0,7]])),{2:16,0:11})
    def test_original_native_counterexample(self):self.assertTrue(conserved([[2,6],[2,4],[2,6]],[[2,42],[2,4],[2,6]],[[2,36],[0,56]],[[0,56]]))
    def test_transfer_into_last_duplicate_slot(self):self.assertTrue(conserved([[2,6],[2,4]],[[2,6],[2,40]],[[2,36]],[]))
    def test_fake_hero_gain_rejected(self):self.assertFalse(conserved([[2,6],[2,4],[2,6]],[[2,42],[2,4],[2,6]],[[2,36]],[[2,36]]))
    def test_fake_missing_gain_rejected(self):self.assertFalse(conserved([[2,6],[2,4],[2,6]],[[2,6],[2,4],[2,6]],[[2,36]],[]))
    def test_species_substitution_rejected(self):self.assertFalse(conserved([[2,16]],[[2,16],[4,36]],[[2,36]],[]))
    def test_hidden_casualty_rejected(self):self.assertFalse(conserved([[2,16],[4,10]],[[2,52],[4,9]],[[2,36]],[]))
    def test_split_without_transfer_not_delivery(self):self.assertFalse(conserved([[2,16]],[[2,6],[2,10]],[[2,36]],[[2,36]]))

if __name__=='__main__':unittest.main()
