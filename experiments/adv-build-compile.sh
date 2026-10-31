#!/usr/bin/env bash
# Isolated build. 8 jobs: the box has 15 GiB WSL RAM and another window may be active;
# VCMI TUs with PCH peak around 1-1.5 GiB each, so 8 is a safe ceiling.
set -uo pipefail
LAB=/root/heroes3-ai-lab
BUILD=$LAB/src/vcmi-adv-build
LOG=$LAB/src/vcmi-adv-build.log
NINJA=/usr/bin/ninja

cd "$BUILD" || exit 1
echo "start $(date -Is)" | tee "$LOG"
"$NINJA" -j8 vcmiclient vcmiserver 2>&1 | tee -a "$LOG"
echo "ninja_exit=${PIPESTATUS[0]}" | tee -a "$LOG"
echo "end $(date -Is)" | tee -a "$LOG"
ls -la bin/ 2>/dev/null | head -20
