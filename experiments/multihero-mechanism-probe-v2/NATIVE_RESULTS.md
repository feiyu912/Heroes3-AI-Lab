# Multihero mechanism v2 native results — 2026-10-23

Status: **engineering qualification only.** This is not a game win-rate, a strategic-strength
claim, or a full-game capability claim. It certifies the isolated hero-exchange close path and one
conservative army transfer under the frozen `multihero-capsules-03` build.

## Qualified runs

| Run | Result | Evidence |
|---|---|---|
| `multihero-probe-close-v2-04` | **v2 engineering pass** | real exchange callback; successful close ACK; no pending query; successful EndTurn ACK; no post-boundary action |
| `multihero-probe-transfer-v2-01` | **v2 engineering pass** | transfer ACK before close; conserved army change; successful close ACK; successful EndTurn ACK; one post-boundary turn notification only |

The transfer changed the donor/receiver armies exactly as follows (from `strategy-trace.jsonl`):

```text
before: hero 0 = {creature 0: 10, creature 2: 3}, hero 2 = {creature 0: 5}
after:  hero 0 = {creature 2: 3},               hero 2 = {creature 0: 15}
```

Thus the transferred 10 creature-0 units are accounted for, and both heroes retain at least one
stack. The one `unexpected_additional_turn` event in the transfer run is recorded as a
post-boundary notification; the audit rejects any move/transfer/close/EndTurn action after the
boundary. No such action occurred.

Key raw hashes:

```text
close-v2-04/probe.jsonl          756a5269f31390ef4c851f5ce93198632131db683cf4ca442b1f61dc08facc93
close-v2-04/strategy-trace.jsonl 26837cbe83909475d477988f8666e21a310d33dc129cb6eb6ee2fd6c951e5de1
close-v2-04/client.log           11da7a1503c563170fc8302b2e3cf4b1ca51fd3eba254242473b6a188570e857
transfer-v2-01/probe.jsonl       a60415da8895e006b3ac4e574bccd799f2af07b11a53cd7c9a2f13ac1b798c38
transfer-v2-01/strategy-trace    806607cb9811b4a779beeeb8dc045265da394676963ad4b3e269cc75c66bb2c1
transfer-v2-01/client.log        10a1d1e2dd9dc3fe5f1c39e510d96e81c59f0c05eef3439813739cae826ef25b
```

The auditor and runner used for these runs:

```text
run_probe_v2.py   50774804982c5c1826f7d349d8d94a1166f0330f9c212151c403d84feba69013
audit_run_v2.py   1e69058d09d2f310de4833030cc0165692154d374673f46df1cadd01febb20ce
```

## Preserved failures and why they are not passes

| Run | Status | Cause |
|---|---|---|
| `multihero-probe-close-v2-01` | startup failure | runner did not create the top-level `Mods` link required by VCMI development mode; client exited before loading a map |
| `multihero-probe-close-v2-02` | startup failure | same missing top-level `Mods` link; the `vcmiclient` symlink alone was not sufficient |
| `multihero-probe-close-v2-03` | native close evidence, audit failure | real close ACK and EndTurn ACK were produced, but the runner included client-mutated `config` files in the frozen-input set; the audit correctly refused `Frozen input changed` |

`close-v2-01` and `-02` are not native mechanism evidence. `close-v2-03` has genuine events but is
not a pass; the clean v2 pass is `-04`, which uses an `initial-config` snapshot and no mutable config
in the frozen hash set.

## Invalid v1 audit

The v1 raw runs remain preserved in `../multihero-mechanism-probe-v1/native-evidence-01`. Their
stored `AUDIT.json` passes are **not usable**: the current v1 auditor requires
`exchange_query_resolved`, but `CGarrisonDialogQuery` never emits that event. The v2 gate is
source-derived and does not require it. The v1 `AUDIT.json` files are not edited.

## Archive

All five v2 run directories, including every failure and the two passes, are copied under
`native-evidence-v2/`. `native-evidence-v2/ARCHIVE.json` contains per-file hashes or symlink
targets and the per-run audit summary.

```text
native-evidence-v2/ARCHIVE.json 90b0cc680fe987642ffef2bee562d53aef1753946d49e3f71afcb32cb15dabfc
close-v2-04/AUDIT_V2.json       f4e2c49221e1f292c1a338fe802345fe178d41d5fcd6a4192237466a77df846a
transfer-v2-01/AUDIT_V2.json    dac53c68abc539b015f82513898432d2834755234c86ea56ed944deffb3d32ef
```

## Limits and next step

This does not demonstrate strategic play, multihero scheduling, learned recruitment, courier
behavior, town delivery, town defense, or an independent win-rate improvement. The next single
mechanism factor is a **two-independent-mobile-heroes scheduler test** with separate reachable
objectives and one blocked/garrisoned control; it must show both heroes receive native legal
move ACKs, not merely appear in snapshots. It has not been run.
