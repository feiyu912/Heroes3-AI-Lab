"""Summarize the completed real capacity ladder from immutable per-stage evidence."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    output = args.root / 'AUDIT.json'
    if output.exists():
        raise ValueError('Refuse overwrite')
    summaries = []
    for size in (8, 12, 24):
        run = args.root / f'scale-{size:02d}'
        resource = json.loads((run / 'RESOURCE_AUDIT.json').read_text())
        raw = json.loads((run / 'INDEPENDENT_RAW_AUDIT.json').read_text())
        release = json.loads((run / 'POSTRUN_LOCK_AUDIT.json').read_text())
        samples = [json.loads(line) for line in (run / 'resources.jsonl').read_text().splitlines()]
        inference = [json.loads(line) for line in (run / 'inference-batches.jsonl').read_text().splitlines()]
        memory = samples[0]['memory']
        gates = dict(raw=raw['passed'], simultaneous=resource['peaks']['simultaneous_pairs'] == size,
            checkpoint_identity=resource['checkpoint_sha256'] == '9a6b15c6be3866d61d8af5fe830471089c39972e57eee6e326828213d5453159',
            zero_optimizer=resource['optimizer_steps'] == 0, no_remaining=not release['remaining_batch_processes'],
            locks_free=all(value == 'free_at_probe' for value in release['locks'].values()),
            available=min(row['memory']['MemAvailable'] for row in samples) >= max(2 * 1024**3, memory['MemTotal'] * .2),
            swap=max(row['memory']['SwapUsed'] for row in samples) - memory['SwapUsed'] <= 256 * 1024**2,
            disk=min(row['memory']['disk_free'] for row in samples) >= 5 * 1024**3,
            rss=max(row['batch_rss'] for row in samples) <= memory['MemTotal'] * .7)
        if size < 24:
            gates['next_prediction'] = json.loads((run / 'NEXT_STAGE_GATE.json').read_text(encoding='utf-8-sig'))['passed']
        else:
            capacity = json.loads((run / 'CAPACITY_SUMMARY.json').read_text())
            gates['balanced_8cells_3_each'] = capacity['balanced_8cells_3_each']
            gates['unique_24_seeds'] = capacity['unique_seeds']
        forward = sum(row['forward_and_sampling_seconds'] for row in inference)
        summaries.append(dict(environments=size, gates=gates, passed=all(gates.values()),
            samples=resource['accepted_samples'], seconds=resource['wall_seconds'], peaks=resource['peaks'],
            forward_seconds=forward, forward_fraction=forward / resource['wall_seconds'],
            checkpoint_sha256=resource['checkpoint_sha256'], source_sha256=resource['source_sha256']))
    manifest_path = args.root / 'scale-24' / 'ARCHIVE_MANIFEST.json'
    manifest = json.loads(manifest_path.read_text())
    report = dict(stages=summaries, passed=all(row['passed'] for row in summaries) and manifest['verified'],
        actual_optimizer_steps=0, learning_improvement_claimed=False,
        archive=dict(original_linux_run=manifest['original_linux_run'], files=len(manifest['files']),
                     manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest()),
        caveats=['12-env workload unbalanced', '24-env output filesystem differs; no matched IO causal claim',
                 'Torch memory sampled, not hardware VRAM peak', 'Capacity jobs are not independent ability tests'])
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=report['passed'], stages=len(summaries), archive_files=len(manifest['files']))))


if __name__ == '__main__':
    main()
