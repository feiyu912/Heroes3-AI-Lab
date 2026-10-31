# Scheduler probe: native results and engineering stop

## Run

- Evidence source: `/root/heroes3-ai-lab/evaluations/multihero-scheduler-probe-v1-01`
- Archived copy: `native-evidence-01/`
- Variant: `scheduler`
- Capsule:
  `/root/heroes3-ai-lab/evaluations/multihero-scheduler-capsule-01/scheduler`
- Server mode: native thread server (`useProcess: false`)
- Policy broker: absent
- Seed: `2026102501`
- Final test: not touched
- Training samples: 0
- Optimizer steps: 0

## Native observations

- `turn_open` count: 2
- successful `endturn_ack` count: 1
- controlled stop: true
- timeout: false
- loaded capsule identity: verified
- thread server gate: passed
- failed move ACKs: 0
- changed frozen inputs: 0

Successful mobile move sequences (request ids matched to `move_ack result=1`):

- hero 0: 12 successful sequences; turns 1 and 2; positions
  `(7,10) -> ... -> (17,12)`
- hero 2: 11 successful sequences; turns 1 and 2; positions
  `(10,10) -> ... -> (16,6)`

The scheduler therefore did move two independent owned heroes, and it did so
after a successful turn boundary. This is a mechanism observation only.

## Failure

The intended control hero 3 was not blocked or garrisoned. It was loaded as a
normal mobile own hero and moved from the town area through
`(7,9) ... (7,3)`. The audit found:

- `move_sent_for_non_mobile_hero` (10 occurrences)
- `successful_move_ack_for_non_mobile_hero` (10 occurrences)
- `town_tile_control_moved`
- `town_tile_control_scheduled`
- `native_log_scheduled_control_hero`

Audit result: `engineering_pass: false`.

This does **not** establish scheduler qualification. The fixture's control
condition was invalid. The run must not be described as a pass, and it is not a
win-rate or strategic-strength result.

## Raw hashes

- `probe.jsonl`:
  `25ea6914583c4b2ec2b58bfc29751c2d9e3f9964a41912eeadef50ffcb82acae`
- `strategy-trace.jsonl`:
  `0a6a4d3d42c451430b0c73dcec3eb8b6210d88fd0298b095e1ccb8ef7406ba46`
- `client.log`:
  `8365e92c034b91186773286e2ed9e2d29e2f9da3c08163450a8664eb9b9343d2`
- `plan.json`:
  `04978a018777b3eb3b660a0e9ed227f6d19284882f933948e38e486f290b3bad`
- `execution.json`:
  `4c5d1734be6c241ffb6cc56b7966d1ea51e883f0549dc979c7580aa6721850b7`
- `AUDIT_SCHEDULER.json`:
  `3cb5efcc20837e83e2612de54432d8d39269bba1a73fded656025ba7e0f0a17c`

The complete file hash table is in `native-evidence-01/ARCHIVE.json`.

## Engineering stop

Per the failure rule, the raw evidence and fixture are preserved. No silent
retry, reseed, or gate relaxation was performed. The next scheduler attempt must
be a new single-factor experiment with a genuinely blocked/garrisoned control,
or a source-derived scheduler change (for example, filtering
`CGHeroInstance::isGarrisoned()` in `pickHero`) followed by a legitimate control
fixture. PPO training and final-test work remain blocked until the scheduler
gate is actually qualified.
