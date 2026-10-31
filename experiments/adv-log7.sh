#!/usr/bin/env bash
D=/root/heroes3-ai-lab/workers/adv-runs/20261017T174544Z-DirectorAI-vs-Nullkiller2-seed2026101801
L=$D/client.log
echo "--- director lines (count) ---"
grep -a -c "DirectorAI:" "$L"
echo "--- first 12 director lines ---"
grep -a "DirectorAI:" "$L" | head -12
echo "--- last 6 director lines ---"
grep -a "DirectorAI:" "$L" | tail -6
echo "--- day progression ---"
grep -a -oE "starting turn, day [0-9]+" "$L" | tail -4
echo "--- tail ---"
tail -12 "$L"
