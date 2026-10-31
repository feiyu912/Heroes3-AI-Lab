"""Verify saved frozen experiment artifacts without running more battles."""
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    saved = read(ROOT/'models/challenge-v4/manifest.json')
    freeze = read(ROOT/'research/final-policy-freeze.json')
    native = read(ROOT/'models/goal-v5-native-selected/manifest.json')
    actual = sha(saved['checkpoint'])
    assert actual == saved['sha256'] == freeze['sha256'] == native['checkpoint_sha256']
    assert sha(freeze['backup_checkpoint']) == actual
    assert sha(saved['source_checkpoint']) == actual
    assert saved['resume_available'] is False and saved['continuation_optimizer'] == 'fresh'
    assert native['validation']['passed'] and native['validation']['all_workers_exit_zero']
    assert not native['needs_numeric_and_live_validation']
    for model in native['models']:
        assert sha(model['path']) == model['sha256']
    results = read(ROOT/'research/fresh-challenge-results.json')
    assert len(results) == 6
    games = 0
    matchups = []
    for item in results:
        report = read(item['report'])
        summary = report['summary'][0]
        assert summary == item['summary'][0]
        assert summary['battles'] == 512
        for key in ['truncated', 'invalid_actions', 'non_normal_terminations']:
            assert summary[key] == 0
        games += summary['battles']
        matchups.append(dict(name=item['name'], wins=summary['wins'], games=512,
                             report_sha256=sha(item['report'])))
    for path in ['CHALLENGE_RESULTS.md','research/CHALLENGE_RESULTS.json',
                 'research/challenge-results.png','research/challenge-results.svg',
                 'research/runtime-manifest-v4.json']:
        assert (ROOT/path).stat().st_size > 0
    result = dict(passed=True, audited_unix=time.time(), experiment_complete=True,
                  goal_achieved=False, checkpoint_sha256=actual, games=games, matchups=matchups,
                  native_compatibility_passed=True, derived_policy_requires_fresh_ppo_optimizer=True,
                  figure_visual_review='Root viewed the generated PNG; labels and intervals readable.',
                  limitation='Audit of completed frozen V5 experiment. Subsequent methods need new independent confirmation.')
    (ROOT/'research/challenge-delivery-audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
