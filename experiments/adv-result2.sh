#!/usr/bin/env bash
W=/root/heroes3-ai-lab/workers/adv-run2
L=$W/client.log
echo "=== winner / turn ==="
grep -a -oE "AIGateway: Player [0-9] \([a-z]+\) (won|lost)|Turn nr [0-9]+" "$L" | tail -4
echo "=== AI construction ==="
grep -a -iE "Creating adventure AI|DirectorAI" "$L" | head -5
echo "=== hero movement by player 0 ==="
grep -a -c "heroMoved\|MoveHero\|moveHero" "$L"
echo "=== battle starts ==="
grep -a -oE "Starting battle of hero[^ ]* attacking[^,]*" "$L" | head -6
echo "=== crashes ==="
grep -a -c "Disaster happened" "$L"
