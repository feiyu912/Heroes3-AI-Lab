# Explicit picked-up cargo regression

Keep the original stock fixture and seed unchanged. The first observed probe took the town's ten Pikemen but delivered the courier's three initial Archers; its generic stack transfer and query close do not prove a supply job succeeded.

A new reviewed cargo-controller capsule must preserve the courier's initial reserve and deliver the actual ten picked-up Pikemen to the main hero. Required actual result: town Pikemen 10 -> 0, courier receives and then loses exactly those ten, main Pikemen 5 -> 15, courier Archers remain 3. Native ArrangeStacks application and exact ACK, real meeting/query close, persistent roles across turns and subsequent legal movement are required. Cargo registration must follow the actual pickup ACK, not a prepared intent. A same-creature merge that cannot be separated safely by whole-stack transfer must close incomplete, never donate the initial reserve or declare success.

This remains a bounded partial engineering probe with no win/loss, optimizer, expert label, sustainable recruitment or native control-state recovery claim. The previous prototype, native record, failed cargo intention and all original inputs remain intact.
