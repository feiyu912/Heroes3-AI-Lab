#!/usr/bin/env bash
L=/root/heroes3-ai-lab/workers/adv-smoke3/data/vcmi/VCMI_Client_log.txt
echo "lines: $(wc -l < "$L")"
echo "--- map related ---"
grep -aiE "\.vmap|MAPS|map database|Found map|mapInit" "$L" | head -20
echo "--- first 12 log lines ---"
head -12 "$L"
