# Historical pilot02 terminal execution audit

Original training.json SHA256 `0b2d81b1978f1c206c27bbf21f147e6386faa8e8375e26edea0fa8b21d3343ba` is unchanged. The original two real PPO updates and weight files are retained.

3 previously valid episodes fail the new stricter execution/event gate; inspect AUDIT.json for exact raw log lines, action records and classifications. This identifies a historical consumption-versus-execution gap and does not revise old rewards, wins/losses or optimizer history.

For the first EmptyAI victory, a new DirectorAI move is issued after BattleEnded and before gameOver, without a matching service-side move/reply. It must not be treated as an executed training action merely because the preceding battle won. A missing final ACK after actual execution is separately classified; real final military visits may instead be confirmed by the server request, same-hero visit and native battle/capture outcome.
