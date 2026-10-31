# Actual saved battle learner restore — separate from native state

Restore owner files: restore_learner.py, check_restore_cpu.py and audit_restore_cuda.py. Trainer/controller/schedule files are owned by the other agent. Old diverse60 support/trainer sources are unchanged.

The actual approved parent is dcaab92162b9c5b4cb9e5d9773067a320fe9b81fe91c1907449d4a7f8374cdaa, saved after30 updates/15360 environment steps. Mode last,658 model tensors,194 trainable parameters,464 frozen parameters. Original Adam order is32 head parameters at1e-5 and162 last-graph parameters at1e-6. The old checkpoint has numerical parameter IDs but no explicit named manifest. We reconstruct the exact ordered names from the frozen graph and original trainer grouping rule, validate all IDs/shapes/dtypes/moments/metadata and bind the complete state to its explicitly approved file SHA plus canonical digest. Named bindings are recorded in cpu-02/NAMED_BINDING.json.

Important correction from the first CPU preflight: overall actual optimizer.step hook count3840 is not equal to max per-parameter Adam step. Actual saved steps are3833 for97 parameters and3826 for97 parameters because role-conditional graphs can skip gradients. The helper restores the real call counter3840 from its approved saved field; it does not derive it from max(moment.step). cpu-01 failed this overly strict initial assumption; cpu-02 passes after correcting it, with frozen source snapshots retaining the successful audit inputs.

The final helper's actual rerun is restore-cpu-final-01, after adding the live model shape/dtype guard; cpu-02 preserves the earlier successful helper snapshot. Both performed actual CPU model and nonempty Adam restoration, exact torch/Python/NumPy RNG state and next-draw replay, and19 malformed-checkpoint rejection checks preserving the live model, optimizer, RNG and counter. CUDA RNG was validated only as a uint8 saved payload with one16-byte device state. No CUDA API was invoked by these CPU checks; they ran the same2.10 CUDA-enabled Python installation on CPU to avoid optimizer-version drift. No optimizer step or native game was run. Only restoration helper evidence is certified here; the trainer/controller owner's separate source files are still undergoing their own preflight/freeze.

APIs:

- prepare(checkpoint, expected_sha) returns actual CPU model, CPU Adam, saved bundle and an approved-boundary reference; no native environment.
- install_counter(optimizer,0), then restore_CPU(bundle,reference,model,optimizer,counter) restores all CPU learning state and real counter. It returns previous updates/env steps and saved CUDA payload; native_fresh_required is true.
- Root may move model to CUDA and call finalize_CUDA(bundle,reference,model,optimizer,counter). It uses optimizer.load_state_dict casting rules; do not manually move noncapturable Adam scalar step tensors to GPU. CPU Adam step state may legitimately remain CPU while moments follow CUDA parameters.
- After capacity/bootstrap probes, immediately before the first actual sample, root may reapply restore_global_rng(bundle,reference,cuda=True). Apply a preregistered LR intervention only after exact Adam restoration; this RNG-only function does not reset LR.

audit_restore_cuda.py defaults to CPU/source inspection. Only root's explicit --execute acquires GPU then pool leases and performs actual CUDA model/Adam/RNG recovery and nine nonmutation rejection cases. That GPU path has not been run by this task.

Restoring the learner does not restore old native battles or closed workers. Old completed update30 is not old curriculum phase15: the next trainer must select an explicit new schedule epoch and local phase0 from a fresh native environment. This helper does not choose training budget, reward, architecture, LR intervention or DEV seeds. Those decisions remain with root and the schedule owner.
