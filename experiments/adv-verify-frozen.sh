#!/usr/bin/env bash
# Verify the frozen battle environment is byte-identical after the isolated build.
set -uo pipefail
BIN=/root/heroes3-ai-lab/src/gym/vcmi/rel/bin
declare -A EXPECT=(
  [libvcmi.so]=bd50e62ccee1c1e22af4d3bb0f18d6dc1fbc80c5bc0f601489cc3662e34b4441
  [libmlserverplugin.so]=d2d1e26c31cb371c53b52a5d4dfdac8f09d329391a8eacbc29ec8df833b458fa
  [vcmiserver]=26ab58b469584dfd58f5ce2fe3502503409962f6c928c59ad7c63d46c8999a05
  [vcmiclient]=8c820049b5f220e19b0f41dc21cb28b15f1114ecc8cf1e0839fff580e32541ab
  [libmlclient.so]=cc8aaea44afd80016f11f8be9404edcea63d109345f6345a0504e60fca1722ae
)
fail=0
for name in "${!EXPECT[@]}"; do
  actual=$(sha256sum "$BIN/$name" 2>/dev/null | cut -d' ' -f1)
  if [ "$actual" = "${EXPECT[$name]}" ]; then
    echo "OK    $name"
  else
    echo "CHANGED $name expected=${EXPECT[$name]} actual=$actual"
    fail=1
  fi
done
echo "frozen_intact=$([ $fail -eq 0 ] && echo true || echo false)"
exit $fail
