# Strategic x4 recruitment DEV decision — 2026-10-23

Status: **DECIDED, no promotion.** This records the conclusion of the bounded
learned-recruitment x4 curriculum branch. The authoritative evidence remains the
files listed below; this note does not replace them.

## Question

Does a TRAIN-only owned-hero starting-army x4 curriculum, applied during one
fresh PPO update from the zero-recruitment prior, improve independently
evaluated DEV play versus the unchanged initialization and the unchanged
control?

## Registered comparison

Four arms, eight paired DEV cells (two maps, both roles, EmptyAI and
Nullkiller2), 32 native games, CPU argmax:

| Arm | Description | DEV wins |
|---|---|---:|
| `minus4_initial` | prior-4 initialization, no update | 4/8 |
| `minus4_updated` | prior-4 initialization, one update | 4/8 |
| `zero_initial` | zero-recruitment initialization, no update | 4/8 |
| `zero_updated` | zero-recruitment initialization, x4 TRAIN update | 4/8 |

Every arm was 4/4 versus EmptyAI, 0/4 versus Nullkiller2, and 2/4 in each role.
The x4 candidate therefore produced **no DEV win change** against either the
zero-initial control or the zero-updated control.

## Decision

The x4 candidate is **not promoted**. The accepted recruitment baseline remains
the zero-prior initialization with SHA
`1510149ef1c2c896e3125e6468e9e58234a8bfc9e4278ad239f9d6840e1c62a1`.

The x4 one-update checkpoint SHA
`6a0bd8f7c800157258e77cdbdece7fdb4da183ae2a86c103ed050fb6af6e876e`
is retained as a valid engineering artifact. It is not an ability improvement.

## Evidence

- DEV result: `/root/heroes3-ai-lab/evaluations/strategic-learned-recruitment-curriculum-x4-dev-20261023-01/RESULT.json`
  SHA256 `6efdbd24b76ec5c8b4649a57248de75ca22947614ebfb5d1722aa62bdcb831d8`;
  32/32 arms normal terminals, 0 training samples, 0 optimizer steps, final test
  untouched.
- Structural/raw audit: `experiments/takeover-20261023/independent-evidence-02/dev-x4-audit-01/AUDIT.json`
  SHA256 `d64ff2f595137174d0e9166f27c86c4ecb109c171c81aa28ed972c69c5d35f73`;
  28,310 raw files and shared-source hashes verified, initial requests identical
  across all four arms, no GPU/native/optimizer work by the auditor.
- Independent full replay: `experiments/takeover-20261023/independent-evidence-02/dev-x4-full-replay-01/AUDIT.json`
  SHA256 `281ef51d331ebd2db490e6d8a937548d90913cbde640a07bfa48fb1e91c8b5b2`;
  32 unique games and 14,011 CPU proposals recomputed exactly.
- Cross-run comparison: `experiments/takeover-20261023/independent-evidence-02/dev-x4-audit-01/CROSS_RUN.json`
  SHA256 `31e1e36f86803910d127349636cf555bd39c25d8b9ffb16a235b0123d61b5162`;
  `minus4_initial`, `minus4_updated`, and `zero_initial` were byte-identical to
  the prior run, and zero-updated cross-run flips and net wins were both zero.

## What moved and what did not

The x4 arm recruited 1,673 times for 3,945 creatures, versus 2,123 times for
2,123 creatures in zero-initial. It also built 116 times (18 income builds),
took 351 end-turns, made 3,372 moves and 813 town moves, and used 259 free
transfers. The extra recruitment and longer trajectories changed no DEV win.

This is a behavioral change without a demonstrated strategic benefit on these
cells. It is not evidence that recruitment itself is useless, nor that the
curriculum is intrinsically harmful.

## Limits

- Eight paired cells are a small developmental sample; the counts are not a
  population win rate and no 95% interval or automatic promotion follows.
- The x4 update used 272 Adam steps; the prior zero-update used 208. The
  comparison is not an equal-Adam causal estimate.
- Training-batch-02 outcomes (4 EmptyAI wins, 4 Nullkiller2 losses) are training
  outcomes, not promotion evidence.
- Byte-identical unchanged arms rule out evaluator drift for this comparison;
  they do not establish hidden-world determinism after policy paths diverge.
- Public unit-count decreases are not certified combat casualties.

## Next gate

The strategic branch is closed at this boundary. The next registered work is the
battle phase-end terminal-drain prefix-credit qualification (2,048 actual native
transitions, zero optimizer steps), followed by paired microtraining only if
that qualification passes. No further strategic training branch starts until
that stage is resolved.
