# Native epoch and strict model recovery

The validated CUDA checkpoint at
`strategic-vector-v1/native-cuda-boundary-clean-4env-01/continuous-2/update-2.pt`
belongs to the accepted **server-ready-v8** native/source epoch. Its two updates
and exact continuous/split/resume comparison used that epoch, not a future
threat-release or typed-action implementation.

A recoverable archive is retained at
`/root/heroes3-ai-lab/src/vcmi-adv-variants/server-ready-v8/`: the Director source
and header, three server-barrier source files, client/server/library binaries,
and native config. Other native sources are unchanged and recorded in the
phase-A baseline's complete source manifest. Original frozen battle binaries
are separate and remain unchanged.

Changing Director source intentionally invalidates strict same-protocol PPO
resume. Do not disable that guard. Either restore the archived source/runtime
and verify every checkpoint protocol input, or explicitly initialize a new
protocol from weights and record the parent SHA plus optimizer/RNG resets.

Never replace source, binaries, config or frozen inputs while a simulation or
learner uses them. Any future restoration must first hold the GPU and pool
leases in that order, preserve the current epoch, restore exact archived bytes,
and verify their hashes. If incremental builds were performed with other
Director headers, restore source with a fresh modification time and rebuild
before future compilation; stale object/static-library artifacts must not be
silently linked into an accepted variant.

Historical input paths may later point to a new epoch. Rechecking an old run
must use its retained source snapshot and archived runtime SHA, rather than
mistaking a deliberate later source change for mutation during the old run.
