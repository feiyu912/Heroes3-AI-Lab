你是用户授权的独立只读方法审核员，实际模型mini / MiniMax-M3.1-Flash，运行于DeepSeek Harness。所有工具禁用。不得调用工具、执行训练、访问任何文件或网络。仅根据以下实施者报告批判拟议方案的混杂、遗漏资格门和结论上限，中文最终回答500字以内、最多3点。不输出长篇思考，不将审核视为运行授权。没有原始日志或源文件提供，不能声称核验了原raw。

实施者报告：原始TRAIN-only12格已全部通过独立12原生重审+11058CPU完整proposal，兵量×1/×2/×4赢0/4、1/4、2/4；×4两胜仅矿图红蓝，发展TRAIN图仍两败。模型固定手工zero初始化151014...，未PPO/未专家标签。

拟下一实验：两臂从同一151014完整权重开始，各自新Adam/RNG链，共同采样/优化种子。每臂同两TRAIN图×两角色×EmptyAI/NK=8完整随机on-policy新局；仅curriculum臂对NK的己方起始英雄兵量×4，control全×1，EmptyAI均×1。同schema6/capsule02/network/reward(完整±1,episode-balanced)/LR3e-4/一次4epoch PPO。承认episode长度与实际Adam数可能不同：这是相同完整cell/one-update算法，而非等Adam纯计算对照；不强制补步。禁止把本次argmax校准数据准入PPO。

独立24DEV为共同初始8+control更新8+curriculum更新8：原始未加兵DEV、新固定seed，训练后只评一次，无model selection，不触finaltest。已发现旧collector采样seed_material含实际map名，x1/x4别名导致不同随机流；新epoch改为canonical原始TRAIN map名+role/op/seed/logical_update，两臂一致。新隔离policy/run格式、源冻结、角色/倍数/精确8格/资源锁和真实catalog/ACK审计保持。

请指出最关键的混杂或错误/缺失，提出执行前必须预注册的最少资格门；特别注意相同seed不代表环境分歧后逐动作配对、兵量既影响难度也改变状态分布/胜率奖励、少量DEV与两图可支持何种有限判断、单次PPO与CPU proposal通过不能替代何种独立验证。不要把没有显著性当作不能开展工程试验，也不要虚构已失败/已通过。