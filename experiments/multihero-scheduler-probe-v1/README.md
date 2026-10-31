# Multihero scheduler probe v1

## Scope

This experiment isolates the adventure-layer scheduler. It does not train, does
not use the policy broker, and makes no strength or win-rate claim. It uses a new
capsule built from the accepted shared source with one variant: the original
`CDirectorAI::pickHero` / `findTarget` scheduler plus the existing native probe
event hooks, with the v1 single-turn meeting stop removed.

The question is narrow:

> Can the native Director scheduler issue and receive successful move requests
> for two independent owned mobile heroes across at least two own turns, while
> not scheduling a designated control?

## Source and build

- Accepted source: `/root/heroes3-ai-lab/src/vcmi-adv/AI/DirectorAI/CDirectorAI.cpp`
- Candidate: `candidates/scheduler/CDirectorAI.cpp`
  SHA-256 `a5ddb88cd663199efdad72e70503db475b9d176924e5cdff46d2aefa52122003`
- Candidate header: `candidates/scheduler/CDirectorAI.h`
  SHA-256 `eaff4a2713c280da3d0f08aafeed824c971ac9586115f8532ca065bc3259164b`
- Capsule: `/root/heroes3-ai-lab/evaluations/multihero-scheduler-capsule-01/scheduler`
- Build attestation SHA-256:
  `eb432d9858cfd938ca609020609fc0da3798d560f42620c23b7f0a52c107da27`
- Scheduler `libvcmi.so` SHA-256:
  `bd4156250f158f0664bb28494b58417607d80a84ee990e5bd1174a99c8d28c2a`
- Accepted binaries were restored and verified after the build.

The candidate restores the original scheduler but keeps probe instrumentation:
`move_issued`, `move_sent`, and `move_ack` now carry the hero id. It also allows
more than one own turn and restores the accepted per-turn move cap. Exchange and
close handling are unchanged.

## Fixture

`fixture-01.vmap` was derived from
`takeover-v2-train-01-mines.vmap` (source SHA-256
`0ccc185c66b1379e8a9522ca81dc6e1567f540aefb104d0b1602e23ad538d036`).
Fixture SHA-256:
`aa50587cb8ced39df3f1e1a476a00bde5cdfbb16c6a8dc12ddfdebbff5498e13`.

Intended layout:

- owned mobile heroes: 0 and 2, at separate positions with separate visible
  resource pickups;
- control: hero 3 on the own-town tile `(8,8)`;
- enemy/control: blue hero 1;
- no monsters, no exchange, no battle.

The run showed that hero 3 was not actually a blocked or garrisoned control.
It was loaded as an ordinary mobile own hero and was selected by the scheduler.
The fixture therefore did not test the intended control condition.

## Gate

The audit requires all of:

1. frozen input hashes unchanged;
2. native thread server and loaded capsule identity verified;
3. at least two own `turn_open` events and a successful EndTurn ACK between
   them;
4. for both hero 0 and hero 2, a `move_sent` with a matching `move_ack result=1`;
5. successful mobile moves observed in at least two distinct own turns;
6. no successful move request for any other hero;
7. no movement by the intended control hero 3;
8. actual position changes for both mobile heroes;
9. no native query/apply rejection.

A failure is an engineering stop, not a reason to weaken the gate.

## Result

**Not qualified.** The native run
`/root/heroes3-ai-lab/evaluations/multihero-scheduler-probe-v1-01` completed two
own turns and both mobile heroes 0 and 2 produced successful move ACKs on both
turns. However, the intended control hero 3 was also scheduled and moved. The
gate failed. Raw evidence is preserved in `native-evidence-01/` (see
`ARCHIVE.json`) and the source run remains under `evaluations/`.

No PPO training, final-test evaluation, promotion, or strategic-strength claim
was made.

See `NATIVE_RESULTS.md` and `SOURCE_REVIEW.md`.
