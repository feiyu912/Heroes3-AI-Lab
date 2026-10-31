# Source review for the v2 closure gate

This review uses the preserved WSL source `/root/heroes3-ai-lab/src/vcmi-adv` and the source
snapshot in `multihero-capsules-03`. It explains why the v1 `exchange_query_resolved` requirement
cannot be satisfied by the hero-exchange dialog.

## Native path

- `lib/mapObjects/CGHeroInstance.cpp:579-588`: visiting a nonenemy hero calls
  `gameEvents.heroExchange(visiting_id, visited_id)`.
- `server/CGameHandler.cpp:1660-1676`: creates `CGarrisonDialogQuery`, sends `ExchangeDialog` with
  its query ID, and adds the query.
- `client/NetPacksClient.cpp:779-781`: dispatches `ExchangeDialog` to
  `IGameEventsReceiver::heroExchangeStarted`.
- `server/queries/MapQueries.h:54-64`: `class CGarrisonDialogQuery : public CDialogQuery`; its
  only overrides are the constructor, `notifyObjectAboutRemoval`, and `blocksPack`. It does not
  override `onRemoval`.
- `server/queries/MapQueries.cpp:61-76`: the implementation likewise has no `sendQueryResolved`
  call.
- `server/CGameHandler.cpp:1685-1690`: `sendQueryResolved` exists, but `MapQueries.cpp` calls it
  only from `CHeroLevelUpDialogQuery::onRemoval` (around line 241) and
  `CCommanderLevelUpDialogQuery::onRemoval` (around line 310). Neither is the exchange query.
- `server/CGameHandler.cpp:3637-3653`: `queryReply` verifies the player's top query, verifies that
  it ends by player answer, stores the reply, and pops it. The successful `QueryReply`
  `PackageApplied` is therefore the native close acknowledgement.
- `client/NetPacksClient.cpp:977-980`: `visitQueryResolved` calls
  `IGameEventsReceiver::queryResolved`; because no `QueryResolved` pack is sent for this query,
  the AI callback is never invoked. The v1 raw logs correctly show no such event.

## Consequence

A valid gate must use the native close ACK plus the absence of a still-blocking query, followed by
a successful EndTurn ACK. Requiring `exchange_query_resolved` for `CGarrisonDialogQuery` is a
source-level error, not evidence that the close failed. The old v1 `AUDIT.json` claimed a pass
without that event; that audit is invalid and must not be cited as independent qualification.

## What v2 adds

- It is independent of the stored v1 `AUDIT.json`; it reads raw events and trace state.
- It requires the actual close ACK, `pending_queries=0`, `query_requests=0`, and a subsequent
  successful EndTurn ACK.
- It requires transfer ACK before close for `transfer-close`, and conservation checks.
- It allows only `unexpected_additional_turn` as a post-boundary notification; any additional
  move/transfer/close/endturn action is a failure.
- It preserves the unhandled negative control and every old failure directory.
