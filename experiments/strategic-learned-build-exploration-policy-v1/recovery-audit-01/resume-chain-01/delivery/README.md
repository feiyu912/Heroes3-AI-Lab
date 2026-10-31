# Verified strategic training checkpoint

Final model: model/update-4.pt, SHA256 24b8c3f3d5ddacd61e48bd87a526c1fd59b2a83eafbdacfe44bd5ddcfb5d3e6d.

32 complete Training games,8012 policy rows,130 actual builds (98 infrastructure,26 dwelling,6 income). Four updates in this optimizer epoch total504 Adam steps; ancestor188 belongs to an earlier reset epoch and is not added. Update1 explicitly reset Adam; updates2/3/4 restored and continued the same optimizer and exact protocol.

All three continuation rounds and the copied CPU checkpoint were verified; original Linux evidence is retained. Root independently completed actual CUDA model/Adam/stop/build-moment/RNG restoration with six invalid-resume rejection checks; copied evidence is verification/GPU_RECOVERY_AUDIT.json.

These are training and recovery facts, not a claim of stronger independent performance. Separate fixed paired DEV remains the capability assessment. DELIVERY_MANIFEST.json binds every copied source and destination SHA.
