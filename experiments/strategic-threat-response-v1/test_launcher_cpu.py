from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_phase_a as runner

class LauncherTest(unittest.TestCase):
 def sources(self):
  return dict({str(runner.DIRECTOR):runner.BASE_SHA},**{str(runner.NATIVE/p):s for p,s in runner.SERVER_SHA.items()},other='fixed')
 def test_exact_eight_pairs(self):
  jobs=runner.jobs();self.assertEqual(len(jobs),8)
  self.assertEqual({j['seed']for j in jobs},{2026101881,2026101882})
  self.assertEqual({j['opponent']for j in jobs},{'Nullkiller2'})
  self.assertEqual(len({(j['map'],j['role'],j['seed'])for j in jobs}),8)
 def test_baseline_source_identity(self):
  source=self.sources();runner.compare_sources(source,source,'baseline')
 def test_candidate_only_reviewed_delta(self):
  base=self.sources();candidate=dict(base);candidate[str(runner.DIRECTOR)]=runner.CAND_SHA
  runner.compare_sources(base,candidate,'candidate')
 def test_unreviewed_candidate_rejected(self):
  base=self.sources();candidate=dict(base);candidate[str(runner.DIRECTOR)]='unknown'
  with self.assertRaises(ValueError):runner.compare_sources(base,candidate,'candidate')
 def test_server_delta_rejected(self):
  base=self.sources();candidate=dict(base);candidate[str(runner.DIRECTOR)]=runner.CAND_SHA
  candidate[str(runner.NATIVE/'server/CGameHandler.cpp')]='changed'
  with self.assertRaises(ValueError):runner.compare_sources(base,candidate,'candidate')
 def test_added_source_rejected(self):
  base=self.sources();candidate=dict(base,added='file')
  with self.assertRaises(ValueError):runner.compare_sources(base,candidate,'candidate')
 def test_new_binary_needs_compiled_attestation(self):
  with self.assertRaises(ValueError):runner.validate_build(dict(candidate_source_sha256=runner.CAND_SHA,binaries={'a':'old'}),{'a':'new'})
  runner.validate_build(dict(candidate_source_sha256=runner.CAND_SHA,binaries={'a':'new'}),{'a':'new'})
 def test_terminal_identical_ready(self):
  terminal=dict(event='defeat',day=1,heroes=[])
  self.assertEqual(len(runner.terminal_tail([(1,terminal),(2,dict(terminal,event='native_battle_ready'))])['transport']),1)
 def test_terminal_action_rejected(self):
  for event in ('before_move','threat_commit_released','move_applied','unknown'):
   with self.assertRaises(ValueError):runner.terminal_tail([(1,dict(event='defeat')),(2,dict(event=event))])
 def test_terminal_state_change_rejected(self):
  with self.assertRaises(ValueError):runner.terminal_tail([(1,dict(event='defeat',day=1)),(2,dict(event='native_battle_ready',day=2))])
 def test_no_and_duplicate_terminal_rejected(self):
  for states in ([],[(1,dict(event='victory')),(2,dict(event='defeat'))]):
   with self.assertRaises(ValueError):runner.terminal_tail(states)
 def test_terminal_numeric_type_change_rejected(self):
  with self.assertRaises(ValueError):runner.terminal_tail([(1,dict(event='defeat',day=1)),(2,dict(event='native_battle_ready',day=True))])
 def test_frozen_file_change_rejected(self):
  with tempfile.TemporaryDirectory()as folder:
   p=Path(folder)/'input';p.write_text('old');freeze=runner.hashes([p]);runner.verify(freeze);p.write_text('new')
   with self.assertRaises(ValueError):runner.verify(freeze)
 def test_seed_collision_metadata_only(self):
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);(root/'plan.json').write_text('{"jobs":[{"seed":2026101881}]}')
   self.assertEqual(runner.seed_conflicts(root)[0]['seeds'],[2026101881])
 def test_import_does_not_launch(self):
  with patch.object(runner.subprocess,'Popen',side_effect=AssertionError('No game permitted')):
   self.assertEqual(len(runner.jobs()),8)
 def test_repeat_rejects_changed_model(self):
  with tempfile.TemporaryDirectory()as folder:
   root=Path(folder);(root/'plan.json').write_text('{"jobs":[],"checkpoint_sha256":"wrong"}')
   with self.assertRaises(ValueError):runner.repeat_seed_coverage(root)

if __name__=='__main__':unittest.main()
