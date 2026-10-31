# BC data contract — schema6 strategic decisions

This contract is deliberately narrower than "watch a video and label the best
move".  It defines the only records the offline trainer will accept, so the
other machine can prepare data without guessing the project's interface.

## 1. Unit of data

A record is **one real native policy request + one candidate index**.  The
request is the exact JSON object the engine wrote to
`agent/request-XXXXXXXX.json` (schema `strategy-candidates-v6`).  The action is
the index into that request's `candidates` array.  Candidate order is part of
the action identity; do not reorder candidates.

Minimum record:

```json
{
  "request": { "schema": "strategy-candidates-v6", "request_id": 42, "...": "..." },
  "action": 17,
  "action_type": "move",
  "episode_id": "takeover-v2-train-01-mines-p0-nk-seed2026104402",
  "split": "train",
  "return": -1.0,
  "source": {
    "kind": "script",
    "trajectory_origin": "engine_execution",
    "creator": "video-rule-teacher-v1",
    "version": "2026-10-31",
    "source_reference": "https://... (metadata only; no media redistributed)",
    "permission": null,
    "verified": false,
    "action_origin": "engine_executed"
  }
}
```

Trajectory wrapper:

```json
{
  "record_type": "episode",
  "episode_id": "map-p0-nk-seed...",
  "split": "train",
  "source": {"kind": "script", "trajectory_origin": "engine_execution"},
  "decisions": [
    {"request": {"...": "..."}, "action": 3},
    {"request": {"...": "..."}, "action": 9}
  ],
  "outcome": {"winner": 0, "completed": true}
}
```

`action_type` is optional; if present it must equal
`request.candidates[action].op`.  `return`/`value` is optional and only used
for an auxiliary value target.  `split` must be `train`, `validation`/`val`, or
`test`; `unspecified` is accepted only when the trainer is explicitly doing an
episode-level holdout.

## 2. Request requirements

`validate_dataset.py` calls the frozen `encoder.validate` on every request.  In
particular:

- `schema` is exactly `strategy-candidates-v6`;
- `economy_epoch` is `learned-economy-build-recruit-v1`;
- `own_hero_count` is 1;
- `creature_catalog_sha256` is
  `031d9200e3efa40e2dd82363547d6f39e8f1381296f000d8b83b158ca663eb1e`;
- every `move` candidate has `kind`, `position`, `next`, `path_cost`,
  `heuristic_score`;
- every `build` candidate has an owned town, a legal-looking cost, and exact
  category;
- every `recruit` candidate has the actual town/stock/army bindings, a
  deduplicated quantity bucket, and an affordable exact cost;
- `end_turn` has only `{"op": "end_turn"}`;
- the candidate array is nonempty and bounded.

The trainer never repairs a request.  A malformed or stale request is rejected.

## 3. Source rules (important for video-derived knowledge)

The project already has a hard lesson: a video's **advice** is not a recorded
action.  See `experiments/expert-knowledge-v1/` and
`experiments/human-tactics-events-v3/CURRICULUM_RESULTS.md`.  The following are
distinct:

| Evidence | May be a BC label? |
|---|---|
| A human actually played and we captured the engine request + chosen action | Yes, `human_recorded` (Q3 only after the full evidence gate) |
| A rule teacher derived from a video plays the real engine and the engine logs the chosen action | Yes, `experimental_reconstruction` / `engine_executed`, normally Q2 |
| A human watches a video and guesses "the player probably moved here" | **No** — rejected as `video_guess` |
| A high-level tactic ("build income first", "bait retaliation") | Not by itself; implement it as a teacher/rule or a reward/curriculum, then generate real trajectories |

The accepted `source.kind` values are `script`, `search`, and
`human_structured`.  `source.trajectory_origin` is `engine_execution`,
`human_recorded`, or `experimental_reconstruction`.  An `action_origin` of
`video_guess` is rejected.  Unknown fields must be `null`, never invented.

If the other machine only has video notes, the most reliable preparation is:

1. write a deterministic teacher module (`choose(request) -> candidate index`)
   implementing the notes;
2. run that teacher in the real isolated engine on the registered TRAIN maps;
3. let the engine write the exact requests and the teacher's chosen indices;
4. export those trajectories in the JSONL format above;
5. validate legality and coverage;
6. train BC.

This makes every label executable and auditable.  It does not prove the teacher
is optimal; that is what the paired evaluation is for.

## 4. Splits and leakage

- Split by **episode / map / seed**, never by individual decisions from the same
  game.  The validator rejects exact request hashes that appear in two splits.
- A validation game must not share its map+seed+role with a training game.
- Keep a final test split untouched until the model and teacher rules are
  frozen.  Do not select the number of epochs or the checkpoint on the final
  test split.
- If the dataset has no explicit split, `train_bc.py` holds out entire episodes
  by a seeded hash.  This is a fallback, not a substitute for a pre-registered
  split.

## 5. Quality and size gates

Hard gates enforced now:

- every request validates;
- every action is a legal candidate index;
- catalog SHA and encoder version match;
- `video_guess` is rejected;
- Q0 records are rejected;
- `--quality-gate q3` rejects anything not explicitly `Q3`;
- exact cross-split request leakage is rejected;
- conflicting labels for the exact same request are rejected (the first is not
  silently kept by the trainer; the validator reports the conflict).

Recommended before a real training run:

- at least 10,000 unique decisions for a first BC fit; 50,000+ if the teacher
  covers multiple maps/opponents/roles;
- all four action types present with at least a few hundred examples each;
- both player roles (0 and 1) and both opponent families
  (`EmptyAI`, `Nullkiller2`) represented in TRAIN;
- at least two maps, with a held-out map family for validation;
- Q3 labels for any claim of "verified expert"; Q2 is exploratory only.

More data is not automatically better: a large set of weak teacher actions can
make the policy confidently mediocre.  The teacher must be stronger than the
student on the same states, or the BC stage has no reason to help.

## 6. What to deliver from the other machine

Deliver a directory containing:

```
bc-dataset/
  train.jsonl
  validation.jsonl
  test.jsonl                 # optional; keep sealed until freeze
  DATASET_AUDIT.json         # output of validate_dataset.py
  TEACHER.md                 # rules, sources, limitations, what was NOT labeled
  SOURCE_SHA256.json         # hashes of code/rules used to generate labels
```

If a trajectory was generated by a teacher, include the teacher source hash and
the exact engine/capsule identity.  If it was human-recorded, include the
recording provenance and permission status.  Do not include game data, videos,
or personal information in the repository.

## 7. What this data cannot do yet

The current schema6 action space is a **single-hero** policy over
`move` / `end_turn` / `build` / `recruit`.  Battles are delegated to native
BattleAI; free transfers are scripted.  Video advice about:

- multiple heroes and hero chains,
- hiring heroes or tavern play,
- town-only neural management beyond the exposed build/recruit candidates,
- army splitting/merging outside the scripted transfer,
- active hero spells, town portal, dimension door, fly,
- adventure-map guards, scouting, and long-range pathing,

cannot be turned into a label in this interface.  Either extend the interface
first (new observation/action epoch and new qualification), or restrict the BC
dataset to the current action set and state that limitation explicitly.
