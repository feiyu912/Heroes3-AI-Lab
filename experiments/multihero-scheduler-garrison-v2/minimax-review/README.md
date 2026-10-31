# 实际 DeepSeek Harness / MiniMax 委派证据

通过本机正常 CLI `H:\DeepSeek Harness\resources\runtime\cli\bin\dsh.cmd` 派发，使用现有 mini / MiniMax-M3.1-Flash 路由与 dsh 自身 credentials service；未打印密钥、未改 desktop 配置、未改原聊天、未切模型。会话日志写本专用目录。

初轮以TASK.md列明7份研究文件完整文本，禁用全部文件/执行/网络/子代理工具。实际请求仅残留exit_plan_mode。其返回 max-tokens，output 32768，final空，不能当作审核。见 INITIAL_FAILURE.md 和根events/session。

单次纠正调用位于corrective-01：核验dsh实际schema和MiniMax官方文档后，显式 reasoning low、maxTokens 4096、零工具；仅给实施代理的v2失败观察和v3几何隔离方案，要求500字内回答。实际completed、input 720/output 476，最终审核在 corrective-01/REVIEW.md。REQUEST_ATTESTATION.json从真实压缩会话抽取，证明模型与实际4096/low。

限定：成功的是外部审核委派，不是scheduler资格；这是仅基于实施者报告的方法审核，未独立读取原生日志。根RESULT.json汇总并存最终材料哈希。源证据和freeze/资源锁未修改，未运行编译/native/GPU/训练。
