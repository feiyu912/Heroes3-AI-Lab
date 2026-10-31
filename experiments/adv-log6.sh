#!/usr/bin/env bash
L=/root/heroes3-ai-lab/workers/adv-run2/client.log
echo "--- tail ---"
tail -40 "$L"
echo "--- errors ---"
grep -a -n -iE "error|exception|assert|terminate|shutdown|Ending current game" "$L" | tail -10
