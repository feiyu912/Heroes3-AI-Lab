# 普通战斗保留开发诊断

本目录只比较预先固定的B64、Human Q2 BC、source WAIT BC；不是新独立测试，也不据此宣称完成长期胜率目标。

retention-plan.json已冻结48个开发场景192..239、双方角色、每条件一个固定引擎种子、BattleAI与原始公开MMAI_MODEL两种对手。每模型每对手96局，6任务共576局；12评测workers，串行运行。模型不能在此替换成测试后挑选的新版本。

准备与CPU静态检查已实际执行，见static-check.json。已核对地图、初始B64和原生公开ONNX文件SHA；未启动评测、GPU或游戏。

根任务统一排程后运行：

```bash
/root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/expert-retention-v1/run_retention.py
```

只重做准备/静态检查则加`--prepare-only`。计划、控制器或固定输入有差异时拒绝执行，不静默更新冻结计划。

实际评测由原research/evaluate-battles.py取得共享flock，控制器外层不持同一锁，避免子进程死锁。模型推理走CPU；eval进程及模拟器只在根任务启动此控制器后创建。新GPU训练若也持同一flock则与这些任务串行。

Human与WAIT候选各自等待训练报告和freeze出现，验证模型/初始权重/报告/数据SHA再使用。等待间隔30秒，仅轮询文件。Human查看recovery-v2/pilot-control.json；WAIT任务管理者须在wait-variant-v2/source-bc-control.json写state=training/completed/failed，训练脚本本身没有该writer。出现明确failed/repair_needed或报告与freeze不一致，控制器写本目录control.json为repair_needed并退出；没有已知控制状态时保持等待，不根据日志缺失臆测完成。

已有评测结果复用前逐项核对checkpoint SHA、48场景、双角色/种子完整96条、对手模型及原生/地图/脚本冻结哈希，原生终局与兵力审计一致。不匹配不会force或改写旧报告。成功后development-results.json列六组真实胜率、角色胜数、截断/非法和损失，仍标独立确认未运行、goal未达成。

当前4条WAIT首步仍有幽灵龙老化/伤害随机性混杂，Human185条也是Q2候选。即使小专项拟合成功，也必须检验普通BattleAI/MMAI能力是否回退；576局开发结果用于诊断，后续冻结新模型另建未读确认集。
