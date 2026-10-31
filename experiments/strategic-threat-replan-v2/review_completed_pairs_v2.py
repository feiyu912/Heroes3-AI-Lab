"""CPU-only independent audit of terminal diagnostic artifacts; never starts games."""
import argparse
import json
from pathlib import Path
from audit_replan_v2 import audit, require, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('pairs', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    result_path = args.pairs / 'RESULT.json'
    result = json.loads(result_path.read_text())
    require(result['passed'] is True and len(result['pairs']) == 8, 'Full diagnostic batch is not terminal/passed')
    result_sha = sha(result_path)
    args.out.mkdir(parents=True, exist_ok=False)
    summaries = []
    for pair in result['pairs']:
        for arm in ('a', 'b'):
            original = args.pairs / f"pair-{pair['pair']:02d}" / arm
            output = args.out / f"pair-{pair['pair']:02d}" / arm
            report = audit(original/'native', original/'raw-audit/AUDIT.json', output)
            for key in ('releases', 'changed_goal', 'changed_next', 'multiple_immediate_next_releases'):
                require(report[key] == pair['arms'][arm][key], 'Original result versus independent audit mismatch: '+key)
            summaries.append(dict(pair=pair['pair'], arm=arm, mode=report['mode'],
                                  proposals=report['proposal_count'], releases=report['releases'],
                                  retained_commit_checks=report['retained_commit_checks'],
                                  audit_sha256=sha(output/'AUDIT.json')))
    require(sha(result_path) == result_sha, 'Original result changed during audit')
    final = dict(passed=True, fixture=False, native_games_reaudited=len(summaries),
                 new_native_games=0, optimizer_steps=0, training_samples=0,
                 proposal_count=sum(x['proposals'] for x in summaries),
                 retained_commit_checks=sum(x['retained_commit_checks'] for x in summaries),
                 releases=sum(x['releases'] for x in summaries),
                 original_result_sha256=result_sha, arms=summaries,
                 source_sha256={str(Path(__file__)):sha(Path(__file__))},
                 limitation='Exact binding and exhaustive bounded-commit audit; no safety/causal superiority certification.')
    (args.out/'AUDIT.json').write_text(json.dumps(final, indent=2))
    print(json.dumps({k:v for k,v in final.items() if k != 'arms'}, indent=2))


if __name__ == '__main__':
    main()
