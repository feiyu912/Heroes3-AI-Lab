# Duplicate creature slots: independent historical impact review

The defect is real, but its effect must be scoped by actual dependencies. `audit_supply_raw.army` constructed `Counter({creature:count ...})`: the dictionary kept only the final slot of a repeated creature. The frozen buggy helper from pilot01 is preserved as `original_buggy_audit_supply_raw.py`. This review uses its own independent slot-summing arithmetic, not tactics' patched helper. It launches no game/GPU and changes no training/native input or original evidence.

## Original fifth-game case

Raw native directory: `/root/heroes3-ai-lab/workers/adv-runs/threat-a-native-pilot-01-baseline-4-2026101881-g2841epm`. Trace SHA256 is `f4848e134f66ed6e92c0f9241bf0da8a7dc45480b76370f59606274c45622d11`, matching the recorded native report. Native day 51, trace lines **2256→2257**, is `before_army_transfer→economy_applied`. Replacement hero **21**, original main hero **2**, receives creature **2** from town **18**:

| Quantity | Before | After | Change |
|---|---:|---:|---:|
| Hero's three creature-2 slots | 6+4+6=16 | 42+4+6=52 | +36 |
| Town creature 2 | 36 | 0 | -36 |
| Old helper's hero count | 6 | 6 | 0, incorrect |

Other army slots are unchanged. The old helper therefore found no changed hero and raised `Ambiguous transfer state`; native did not fail this transfer. All corrected fifth-game transfers conserve troops: **683** delivered total, **340** to original main hero. This specific +36 is to a replacement hero, not the main hero. The original game completed with blue winner; neither this arithmetic review nor correction changes its native outcome. The failed pilot audit/run history remains preserved and is not silently promoted into a completed causal experiment.

## Published historical reports versus new computations

All **24 already-passed historical economy records** (acceptance06's 12 plus 12 earlier accepted records) were recomputed from original matching trace SHA, including transfers and successful recruitment counts. Each record's published transfer total/main total and recruitment total match corrected slot sums. There are zero changed published totals and zero corrected conservation/recruitment failures. Acceptance06 includes one game with repeated slots in 183 state records, but those do not change its recorded transfer deltas. Its original aggregate **3621 total / 3344 original-main** is retained. Earlier 12 accepted economy records total **2010 / 2010**, also unchanged.

Ten published raw audits present in the old supply pilot01 and four published raw audits from threatA pilot01 also have unchanged totals under corrected arithmetic. The old supply folder contains 11 smoke summaries and 10 published raw audits; this review does not invent the remaining games of its originally intended larger pilot. No invalid old lifecycle/game/query result is recertified by correct troop arithmetic.

Additional computations below are **new diagnostic transfer statistics** on archived experiments that did not originally publish these quantities:

| Archived cohort | Games checked | Correct total delivered | Correct delivered to original main | Old-helper behavior when newly applied here |
|---|---:|---:|---:|---|
| CUDA continuous/split/resume | 32 | 3912 | 2786 | Same totals, no duplicate states |
| Paired development | 16 | 5036 | 3625 | Same totals, no duplicate states |
| Capacity 8 | 8 | 867 | 553 | Would reject 3 transfers; other parsed events sum 824 |
| Capacity 12 | 12 | 1663 | 876 | Would reject 3 transfers; other parsed events sum 1620 |
| Capacity 24 | 24 | 3028 | 1633 | Would reject 4 transfers; other parsed events sum 2958 |
| Fresh cleanprior native smoke | 1 | 71 | 71 | Same totals |
| Native turn-start restore | 1 | 71 | 71 | Same totals |

**824, 1620 and 2958 are not numbers from any historical capacity report.** They are counterfactual partial sums from applying the buggy helper during this new review; that helper would have raised rather than produced a valid full audit. The original capacity reports certified samples, execution, resource use and zero optimizer updates, not transfer totals. The ten affected capacity transfer events (+43/+43/+70 across the three runs) all target replacement heroes, so these newly calculated original-main quantities are unchanged. This is no evidence that earlier execution admission was false.

Across the 134 selected archived episode records, corrected transfers and recruitment have zero arithmetic errors and there are no missing trace inputs. Overlapping seeds/continuous versus split reruns are separate recorded executions, not independent strategic strength samples. Complete per-event changed arithmetic, native directories, trace SHA, old-helper errors, corrected totals, and comparisons with published audit files are in `RECOMPUTED.json`.

## Actual dependency and claim impact

| Component | Uses buggy slot helper? | Impact on its actual reported result |
|---|---|---|
| `strategic-policy-v2/audit_supply_raw.py` transfer accounting | Yes, directly | Real false audit rejection in pilot01 game 5. Must use accumulated slot counts. Existing published totals checked here remain numerically unchanged. |
| `strategic-economy-v4/audit_economy_raw.py` | Yes: imports `army` and `audit_episode`; `total_own` used for recruit deltas | Potentially affected. The 24 old passed records were independently recomputed; all published transfer/recruit totals retained. This is component arithmetic review, not full old-native runtime recertification. |
| Native Director action execution, recruiting/transfers | No Python audit helper | Native request/ACK/state and actual troop change are unchanged. No binary/source/model was altered by the audit fix. |
| `collect_vector.audit_native_events`, `parallel_trainer` | No `army`/`audit_supply_raw` dependency | Execution admission checks native requests/decisions/replies/ACKs/query rejections. Its admission and real CUDA training evidence are not invalidated by the independent accounting bug. |
| `episode_balanced_ppo` | No troop aggregation; its Counter counts episode lengths/choices | Samples, terminal rewards, weighted gradients, 116+144 actual optimizer steps and saved parameters are unaffected. |
| `audit_collection_raw` and capacity ladder | Import collector validation/native-event gate; no troop helper | Original sample/IO/native-execution/resource/zero-optimizer claims remain. New transfer statistics are separate diagnostics. |
| `evaluate_dev` and `audit_dev_results` | Native consumption gate from collector; no troop helper | Original paired scores, 5949 actions, validity and lack of win-rate improvement remain. Corrected offline transfer sums add no capability claim. |
| CUDA strict three-directory comparator | Counter used only for event counts and balanced cells; no troop helper | Exact request/action/logp/value/return/model/Adam/global+episode RNG comparison remains intact. Army snapshots are compared as raw request/state evidence, not collapsed by this helper. |
| `verify_native_restore_v3` | Whole raw trace/request/action byte SHA; no troop helper | Exact 117 request/action pairs and three trace files remain byte-identical. Its result is unaffected. |
| Native v3 observation audit | `sum(AIValue*count for each slot)`, no overwritten dictionary | Own hero/town strength recomputation already handles duplicate slots. No migration/visible-information result is withdrawn for this defect. |
| Old `adventure-takeover-v5/economy_audit` / new multihero probe gate | Both increment per creature per slot | Do not contain this particular defect. Prepared probe still has no real compiled/native success claim. |

`DEPENDENCIES.json` records source hashes/import statements for the inspected components. Capacity/development audit owner separately identified `audit_collection_raw.py` and `audit_dev_results.py` as the actual generators; their implementations confirm the dependency distinction. Counter itself is not problematic: constructing a dictionary before Counter is what loses duplicate slots.

## Validation and limits

`recompute.py` reads original raw native traces, verifies their recorded SHA, pairs each transfer/recruit request with its immediately following successful economy state, and recomputes both donor/recipient totals by incrementing every slot. It also independently reproduces old-helper failures for diagnosis. It never overwrites historical reports. `check_cpu.py` passes the exact 16→52 pattern, old 6→6 failure, mixed-duplicate aggregation, slot-order invariance, conservation, and replacement-versus-original-main attribution.

The newly running threatA pilot02 is outside this closed review. The source/helper fix changes audit correctness; it does not change the native policy or establish strategic improvement. Old failed runs remain failed historical evidence, and future mechanism/capability conclusions still require their own complete gates.
