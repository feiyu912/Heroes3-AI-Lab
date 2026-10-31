#!/usr/bin/env bash
W=/root/heroes3-ai-lab/workers/adv-run
L=$W/client.log
echo "--- settings path lines ---"
grep -a -inE "settings|config/|ConfigHandler|vcmi:settings" "$L" | grep -aiE "load|init|file|path|settings" | head -20
echo "--- statsMode mention ---"
grep -a -inE "statsMode|stats" "$L" | head -10
echo "--- files written under W ---"
find "$W" -name "settings.json" -o -name "modSettings.json" | head
