# Acceptance-02 stopped: a spurious movement after server-side game end

Acceptance-02 retained the original four-EmptyAI→eight-Nullkiller2 plan and
stronger explicit final-action checking. The first two engineering games pass:
both train01 roles build33 before32, really recruit/transfer creature0,2,4,6,8,
and confirm every action; original main receives169 troops red and148 blue.

The third game (train02/red/EmptyAI/seed2026101860) has a native red win and
valid file protocol, but its286th movement was never executed. The supervisor
correctly stops with status=failed. The fourth engineering game and all eight
NK development games remain unrun. Earlier failed outputs stay unchanged.

This failure is explicitly **not** an executed terminal visit with only a late
ACK. Native directory:
`/root/heroes3-ai-lab/workers/adv-runs/economy-v4-engineering-map1-red-2026101860-2026101860-aud2uycx`.

- Server log33869 has already sent PlayerEndsGame.
- Client33882 sends a new resource-directed move from(29,9) toward(28,9),
  native MoveHero496, policy request286. It is not the prior winning capture.
- Server33887 receives it,33893 rejects it with "Player is not allowed to
  perform this action!", and33897 explicitly records false application of MoveHero.
- There is no corresponding TryMoveHero, successful displacement, blocking visit,
  battle or capture after this request. Hero position and686 movement remain
  unchanged. Trace1372 records before_move and1373 victory, without its ACK.
- Only33899 does the client receive PlayerEndsGame;33902 invokes gameOver.

Therefore winner alone cannot certify the extra action. This is
spurious_move_rejected_after_server_terminal_before_client_gameover, not
terminal_ack_only or terminal_visit_proof. TERMINAL_CLASSIFICATION.json records
the evidence and allow_as_valid_transition=false. No relaxed audit rule or new
native run has been applied to this failure.

The movement-query unblocking callback can currently resume planning while the
terminal pack is queued behind it. The existing gameOver guard protects only
after gameOver arrives. The raw order also shows the final QueryReply success
and ACK emission occur33878/33879, after the unblock is being handled. An
outstanding queryRequests ACK gate is a concrete next diagnostic: pendingQueries
may already have been erased by QueryResolved while queryRequests remains until
the actual ACK. Native behavior must be corrected and both terminal-with-dialogue
and terminal-without-dialogue paths checked; accepting late ACKs cannot legitimize
an explicitly rejected spurious action. The parent owns native changes; this
audit changes no native files.

AUDIT.json preserves286 issued/285 confirmed movements, the final public request,
all terminal states, full log tail and verified frozen input hashes. No
move_failed/economy_failed state was emitted before process exit, which explains
why checking only those counters would miss this server rejection. The specific
server log evidence is essential.

Client log SHA52335382041e6b6e1d9453e6bf601907286660675a00c792699949788d0ef561.
State trace SHA797ecf2625abf4ac05b4eb69593ed0ebce8c27349e78c0f2052c766d7be24f22.
No full economy acceptance, strategic improvement, expert certification or PPO
update is claimed. BC eligibility remains0.
