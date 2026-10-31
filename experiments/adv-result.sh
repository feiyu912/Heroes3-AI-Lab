#!/usr/bin/env bash
W=/root/heroes3-ai-lab/workers/adv-run2
L=$W/client.log
echo "=== log size / sha ==="
ls -la "$L"; sha256sum "$L"
echo "=== days ==="
grep -a -oE "day [0-9]+" "$L" | sort -t' ' -k2 -n | tail -3
echo "=== game over lines ==="
grep -a -n -B2 -A2 "gameOver" "$L" | head -40
echo "=== winner / result ==="
grep -a -inE "winner|victory|defeat|won|game over|Ending current game" "$L" | tail -15
echo "=== crashes / errors ==="
grep -a -icE "Disaster happened|terminate called|segmentation" "$L"
echo "=== saves ==="
find "$W" -name "*.vsv" -o -name "*.vsgm" 2>/dev/null | head
