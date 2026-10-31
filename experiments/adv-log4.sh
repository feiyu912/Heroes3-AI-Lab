#!/usr/bin/env bash
L=/root/heroes3-ai-lab/workers/adv-run/client.log
sed -n '12,260p' "$L" | grep -n -iE '"server"|"ML"|"statsMode"|"lastMap"|"onlyai"' | head -20
echo "--- does our file have it? ---"
cat /root/heroes3-ai-lab/workers/adv-run/data/vcmi/config/settings.json
