# 干净 venv 补跑：支持集结论复现

在全部 41 包 RECORD 核验通过的新 `native-gpu-verified-20261025` 环境中，使用 `PYTHONDONTWRITEBYTECODE=1`、空 `CUDA_VISIBLE_DEVICES` 和相同未改的 `diagnose.py` 完整补跑，进程正常退出。输入采用纠正 reader 后恢复、与原冻结 SHA 精确相等的 checkpoint61 与 512 行 TRAIN batch。旧环境报告完整保留。

`actual-02/AUDIT.json` 全部原门通过：两目标各 32 个连续组、每个角色 body81 张量；actor 非零支持并集60、critic15，逐组张量及标量支持交集均严格为0。最大 CPU behavior logp 误差仍为 `5.340576171875e-5`，模型和 CPU RNG 未改、`.grad` 未填、GPU 未初始化，优化器步数、native 对局和 DEV 输入为0。

与旧报告的结构和非零支持结果完全相同，部分范数末位有微小浮点差异，因此没有宣称全部数值位级一致。额外的全字段 Python exact 比较曾断言失败，其范围和差异单列在 `EXTRA_BIT_EXACT_COMPARISON_STOP.json` 与 `CLEAN_ENV_REPRODUCTION.json`；原登记审核本身已经通过，没有修改任何门限或重跑选优。完整差值统计见后者。

这次补跑支持在已核验依赖环境中保留“末层 actor/critic 可训练参数支持分开”的结论；仍不证明最终胜负原因或一般模型能力。新 Python 内容资格由 `../python-integrity/PROFILE_CERTIFICATE.json` 及其原详细审核哈希单独绑定。
