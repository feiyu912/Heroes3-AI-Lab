#!/usr/bin/env bash
L=/root/heroes3-ai-lab/workers/adv-run2/client.log
echo "--- ai assignment ---"
grep -a -oE "Player [a-z]+ will be lead by [A-Za-z0-9]+" "$L" | head -4
echo "--- result ---"
grep -a -oE "AIGateway: Player [0-9] \([a-z]+\) (won|lost)|Turn nr [0-9]+" "$L" | tail -3
echo "--- crash count ---"
grep -a -c "Disaster happened" "$L"
echo "--- log size ---"
ls -la "$L"
