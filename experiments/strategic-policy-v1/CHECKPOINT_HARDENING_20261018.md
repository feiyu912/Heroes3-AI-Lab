# 战略 PPO checkpoint 加固与 CPU 复核（2026-10-18）

本次只执行 CPU 工程验证，没有启动游戏、CUDA context、GPU learner 或共享模拟池。未修改 `ppo-pilot-01/02` 历史证据、旧权重或原冻结战斗输入。

## 已改实现

`train_ppo_pilot.py` 新协议 `strategic-ppo-pilot-v2`：

- checkpoint 文件只读一次；同一内存字节同时产生 SHA 和安全反序列化的模型、optimizer、RNG，避免 pathname 被替换后混读。
- 保存使用同目录唯一临时文件、flush/fsync、原子 replace、目录 fsync。失败清理临时文件，不覆盖旧完整文件。
- `--resume` 只接受相同冻结协议、完整 update 边界，并检查 Adam step 元数据和 optimizer 状态一致。checkpoint 内保存原协议，以便延长总 update 数仍可续训。CPU 预检不恢复 CUDA RNG，CPU checkpoint 不采集 CUDA RNG。
- `--initialize-from` 显式仅迁移 prior 格式权重；重置 optimizer、update 编号和 RNG，保存原 checkpoint 路径/SHA/历史 update。与 `--resume` 互斥。改 trainer/原生行为后的旧 update-2 必须迁移，不能称原协议恢复。
- 每次 update 分别记录 actor/critic 相对本次更新前的 changed tensors、L2 delta、max abs delta。原累计字段保留但明示统计基准。
- 正常完成和异常路径均报告实际 Adam step；异常即使发生在某次 step 已应用、回调尚未返回，也从 optimizer state 取实际进度。失败 partial 可保存审计，但明确 `complete_update_boundary=false`，拒绝续训。
- GPU 独占学习器锁前移至 CUDA 初始化之前；最终报告写失败仍释放锁。

当前 trainer SHA：`91a4e3b10f4e16eda9f08ace94f01f8f32dfcc7719ef3c7d60faac727ba02b19`。

## 原始 CPU 证据

最终报告 `checkpoint-cpu-audit-20261018-v4/AUDIT.json`，精确代码快照在同目录 `sources/`。

1. 70 条合成合法请求执行两次 PPO，每次 8 个 Adam step。连续训练与首次更新保存后新模型/optimizer 恢复再更新：模型、Adam state、CPU RNG、Python RNG 逐位一致，总 step=16。actor 和 critic 各 6 个参数 tensor 在单次更新中改变；这仅证明实际梯度更新，不证明战略收益。
2. checkpoint 路径在唯一读取后立刻被测试替换，恢复仍取得同一原始字节的模型、optimizer 和 SHA，未混读新文件。
3. 注入保存中断，旧 checkpoint 字节完全不变，无遗留临时文件。
4. 注入第 3 次真实 optimizer step 后异常：完成回调数为 2，Adam 实际状态为 3。partial checkpoint 保留真实 step=3，resume 被拒绝；协议 SHA、step 元数据错误亦被拒绝。
5. 实际执行 `--preflight --initialize-from ppo-pilot-02/update-2.pt` 和新协议 `--preflight --resume`；通过 mock 将 CUDA RNG 读取/恢复视为硬错误，二者均通过，`torch.cuda.is_initialized()` 始终为 false。迁移 optimizer step=0；合成 resume step=16。
6. 旧 update-2 原始 SHA 与交接一致：`25ff6d18c51698394991ae84c53800d1c8488a0005f172427989e4fed384b5b0`；记录 training_updates=2、Adam 历史 step=176。没有修改该文件。

最早 `checkpoint-cpu-audit-20261018/` 在测试代码中失败：测试把已恢复 optimizer 的原 bundle 当成不可变参考，但 PyTorch CPU load_state_dict 可能复用 bundle 的 state tensor，续训会改变该内存参考。已将测试参考改为独立 deepcopy，后续 v2/v3/v4 通过；该错误不是保存文件损坏或训练器恢复不一致。失败目录保留。

## 可复现命令

```text
wsl -d Ubuntu-22.04 -- /root/heroes3-ai-lab/gpu-venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/audit_checkpoint_cpu.py --out /mnt/g/Heroes3-AI-Lab/experiments/strategic-policy-v1/checkpoint-cpu-audit-new
```

必须使用不存在的新输出目录。脚本使用合成数据执行 CPU optimizer，不获取 GPU/模拟池锁，不把合成数据写作训练游戏成绩。

## 仍未认证

真实原生游戏采样的连续两 update 与边界恢复对照、CUDA 逐位复现和新冻结模型的独立配对能力提升均未由本次 CPU 审计认证。README 已纠正“尚无战略 PPO”的旧说法，保留 pilot-02 两次真实更新、EmptyAI 4胜/NK 4负、第三轮 invalid 不计结果与尚无能力提升证据的事实。
