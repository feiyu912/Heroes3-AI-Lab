# 原生 Ubuntu coherent profile 构造草案

本目录仅准备新 profile 的构造器；尚未运行真实构造、游戏、GPU 或优化器。旧迁出目录、冻结二进制、历史源码、旧 runtime 和旧 Python 环境均不修改。

`build_profile.py` 默认只核输入并打印计划；必须显式 `--execute` 才写新的、此前不存在的 profile。默认独立复制正确字节，不使用硬链接，因此未来在新目录编译或修改文件不会污染旧迁出源。预计主体约10.3GiB，执行前根据证书精确计算空间并要求额外2GiB余量。

构造前要求以下证书全部完成并通过，journal SHA 与条数正确：

- `reextract-full_migrated_lab_files`：27,109份主lab/events普通文件，两个独立payload reader得到相同字节；选择哈希匹配的原迁出文件或`verified-repair`新纠正副本。
- `reextract-critical21`：21份关键模型/程序额外符合迁移前冻结SHA；把必要历史模型复制进新profile相同相对目录，不解包所有worker历史。
- `reextract-runtime_libraries`：17份原运行依赖库的正确原盘字节。
- 原盘`RESTORE.json`与这些源证书绑定同一份已恢复原盘，SHA固定`f90ad98d…5886bc`、209,994,121,216字节。
- Python环境须通过独立的新环境证书，显式传`--venv`与`--venv-certificate`；没有自动沿用已发现payload损坏的旧gpu-venv。证书接口暂为`passed:true`、`environment_root`准确绝对目录、`wheel_record_audit_passed:true`、`packages:41`；根代理的新环境审核若采用其他结构，须按真实证书调整并重做对应检查。

另外要求`reextract-full_lab_symlinks`已完成712条原盘symlink目标资格，`LINKS.jsonl`的SHA、条数和原盘恢复证书绑定通过；每条迁出当前readlink还须与正确原盘目标一致。明确排除了整树尚未展开的主lab evaluations/workers和可重建环境。两个payload reader仍共用同一extfs metadata parser，外部target未被当作已审核内容。

示例（仅在上述证书齐全之后，路径由根代理确定）：

```bash
python3 build_profile.py \
  --out /home/kaicheng/Heroes3-native-profile-01 \
  --venv /home/kaicheng/Heroes3-qualified-venv-01 \
  --venv-certificate /absolute/path/new-venv-audit.json
```

新profile包含两个独立lab目录、`runtime/engine-battle`、`runtime/engine-strategic`、`runtime/game-assets`、`runtime/workers`、17库副本、显式选择的Python环境链接与新入口。编译在二进制里的两个旧cwd只由明确启动进程的`native-paths.so`适配；不在系统全局设置`LD_PRELOAD`。

所有 `/root/heroes3-ai-lab`、`/root/heroes3-ai-lab-events-v2`、`/mnt/g/Heroes3-AI-Lab` 符号链接只在新profile中重定向；相对跨lab链接按原路径词法归一化后映射。其他外部链接不静默修复，所有未解析链接单独列出。源manifest及Python代码内部的历史绝对路径字符串不被改写；新研究入口仍须明确读取环境变量，不能因该profile存在就直接调用任意旧训练脚本。

所有profile的`HEROES3_RESOURCE_ROOT`固定为旧迁出主lab的同一个`evaluations`目录，两个真实锁仍为GPU锁→pool锁。构造器不创建第二套实验锁、不删除旧锁。wrapper也不隐式申请训练资源；实际游戏/训练控制器必须按既有继承FD与inode闸门申请、传递和清理。

`BUILD_MANIFEST.jsonl`记录每个输出普通文件的来源、SHA和字节数；构造后全部再次核验。`SYMLINKS.json`记录原目标、新目标、来源范围与可解析性。工程构造通过不等于完整对局、CUDA恢复、策略强度或所有外部链接可用。

`self_check.py`已用临时小文件验证独立inode隔离、拒绝覆盖/路径逃逸/错误迁出字节、纠正副本选择、证书篡改拒绝、根前缀碰撞不误映射、canonical锁路径及生成脚本语法。结果见`SELF_CHECK.json`；没有用这些synthetic检查代替真实源或游戏资格。较早未接入原盘symlink资格的草稿及当时检查保存在`pre-source-symlink-gate/`，不用于真实构造。
