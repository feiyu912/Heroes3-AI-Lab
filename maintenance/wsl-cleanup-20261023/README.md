# WSL cache cleanup, 2026-10-23

User requested removal of unused WSL contents; research training remains paused.

Removed only42 generated cmake_pch.hxx.gch files inside the three explicitly listed Heroes build directories, and old regenerable npm/NVIDIA/Triton cache files. Also ran apt-get clean successfully. No source, model, evaluation, worker evidence/log, installed environment, native executable or library was deleted. Other projects' data were retained.

Observed free-space increase11379351552bytes (about10.60GiB/11.38GB); df changed151G used→140G used. fstrim completed successfully; its865.9GiB trimmed figure covers all free extents and is NOT the cleanup size or proof of Windows VHDX shrinkage.

Protected frozen native binaries and key recovery models were hashed before/after and matched. PLAN.json, EXECUTE_PLAN.json, DELETED.jsonl, PROTECTED_BEFORE.json, PROTECTED_AFTER.json and SUMMARY.json preserve the exact actions and verification.

Existing programs remain available. A later native rebuild will regenerate the removed precompiled headers and may take longer. Do not confuse absent compiler caches with missing source or failed training. No training/game/compilation was started during this cleanup.
