#!/usr/bin/env bash
W=/root/heroes3-ai-lab/workers/adv-run2
echo "--- disaster context ---"
grep -a -n -A25 "Disaster happened" "$W/client.log" | head -40
