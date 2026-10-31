#!/usr/bin/env bash
L=/root/heroes3-ai-lab/workers/adv-smoke3/try.log
echo "--- error context ---"
grep -a -n -iE "failed to start|invalid|corrupted|reason|error" "$L" | tail -25
echo "--- tail ---"
tail -25 "$L"
