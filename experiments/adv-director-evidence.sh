#!/usr/bin/env bash
D=/root/heroes3-ai-lab/workers/adv-runs/20261017T175208Z-DirectorAI-vs-Nullkiller2-seed2026101801
L=$D/client.log
echo "--- director event counts ---"
printf "ready            %s\n" "$(grep -a -c 'game interface ready' "$L")"
printf "battle callback  %s\n" "$(grep -a -c 'battle callback installed' "$L")"
printf "move issued      %s\n" "$(grep -a -c 'DirectorAI: move hero' "$L")"
printf "move finished    %s\n" "$(grep -a -c 'move finished' "$L")"
printf "no progress      %s\n" "$(grep -a -c 'no progress this move' "$L")"
printf "budget exhausted %s\n" "$(grep -a -c 'move budget' "$L")"
echo "--- reasons used ---"
grep -a -oE "reason=[a-z ]+" "$L" | sort | uniq -c
echo "--- distinct start->dest pairs (top 8) ---"
grep -a -oE "move hero [0-9]+ \([0-9]+,[0-9]+\) -> \([0-9]+,[0-9]+\)" "$L" | sort | uniq -c | sort -rn | head -8
echo "--- move results ---"
grep -a -oE "move finished result=[0-9]+" "$L" | sort | uniq -c
echo "--- progress vs no-progress ---"
grep -a -oE "start=\([0-9]+,[0-9]+\) end=\([0-9]+,[0-9]+\)" "$L" | awk -F'[()]' '{ if ($2==$4) same++; else diff++ } END { print "moved_tiles=" diff, "zero_length=" same }'
echo "--- days reached ---"
grep -a -oE "starting turn, day [0-9]+" "$L" | sort -t' ' -k3 -n | tail -2
echo "--- battles involving red heroes ---"
grep -a -c "Starting battle of hero" "$L"
