# 战术新支线：正交换门禁，尚未原生评估

已读接管入口、人类战术最新进度、原预注册、pilot02原始压缩轨迹及独立审计。
当前仍为0通过整体收益认证的专家课程；旧62条Q3撤销、143条Q2待复核，全部保持隔离。
本目录是可review脚本候选，不是人类专家；没有视频理解、BC、PPO或模型晋升。

## 从原始事件得到的有限结论

`CPU_REVIEW_02.json`重新读取16份原始json.gz，核对对应summary/archive SHA、
全部历史frozen_artifacts，357个真实动作窗口与终局BATTLE_END，并从原始图重算旧候选。
下表仅列旧实验真实改选；伤亡差来自原16局注册全集，不是新候选结果。

|fixture1/角色/seed末四位|step|估值变化permille|严格窗口真实伤害/击杀/反击|最终我方主力损失差|
|---|---:|---:|---|---:|
|attacker/1841|13|-6→0|攻击2伤0杀，COUNTER2伤0杀|0|
|attacker/1842|13|-6→0|攻击1伤0杀，COUNTER2伤0杀|+2|
|defender/1841|11|0→约5|攻击8伤1杀，无COUNTER|-2|
|defender/1842|11|0→约5|攻击8伤1杀，无COUNTER|0|

旧实验teacher与脚本都4/8胜，主力及总体永久伤亡净差0。单兵打出少量伤害、
消耗反击或将负估值改成零，都没有证明后续整体获益。严格窗口只定位这次动作，
不能证明其独自导致最终±2；后续行动、占位和随机数消耗都可能参与。

## 可证伪的新机制假设

只给原visible-exchange增加“候选净估值必须严格>0”门禁，仍要求比teacher高>1
permille。保留teacher非普通近战、未知/非有限估值、WAIT/MOVE/DEFEND/特殊攻击。
候选仍是公开图的一步期望交换估值，绝不称永久单位收益预测或联合搜索。
若新种子完整配对没有改善永久伤亡，或把旧胜变负，假设不通过，不继续训练。

`visible_exchange.py`纯核与图适配都只读公开nodes/edges/active_action_ids以及
当前合法teacher动作；无seed、终局、事件、旧质量标签、隐藏反击次数或未来RNG。
合法集合/actor不符、特殊攻击、未知/NaN/Inf、恰好1的改进阈值等有明确检查。
`experts_events.py`为旧文件字节复制，只调用其assess图解码；历史命名不赋予专家资格。

## 已执行的CPU检查

- 24个合成反例/边界检查通过，包括负到零禁止、严格正数可选、恰好阈值不改、
  非同actor/特殊动作不改、未知/非有限值回退、重复/缺失合法数据拒绝、并列确定性。
- 357个原生归档观测的合法选择、事件窗口、图输入不变检查通过；向输入加入
  seed/event/outcome/withdrawn-label/future-RNG污染字段后，所有选择及质量元数据不变。
- 旧实际4次改选全部按原始图重算精确一致。新脚本在这4个状态中阻止2次攻方零交换、
  保留2次守方正交换。覆盖全部旧teacher和旧脚本后继状态时，新脚本有4次改选、
  相对旧脚本6处动作差异；其中2处是旧teacher后继状态，不能据此预测新轨迹结果。
- 默认launcher实际完成两TRAIN地图及原生依赖SHA冻结检查，打印plan-only，未建runs/worker。

CPU_REVIEW_01是先前一次成功检查；02增加历史冻结输入和summary SHA核验，均保留。
CPU图重放不创建VcmiEnv，不运行游戏、编译或GPU，不占simulation锁。

## 待主agent安排的原生实验

`PREREGISTRATION.md`冻结16新局：TRAIN0/1×双角色×两个新seed2026111801/02×
teacher2/新脚本，BattleAI对手，串行共享池锁。锁定dev/test未用。胜负、主力
永久伤亡、总体永久伤亡分别报告；即时reward仅归档，不作为策略/训练/晋升奖励。
没有学习器。若以后另开学习协议，终局胜负+1/-1/gamma1也须单独注册，不由本轮启动。

完整收益门槛比旧版增加总体伤亡不恶化：16合法正常局、至少2角色/fixture格改选、
无胜转负、总体主力损失严格下降、总损失不增加、两地图各自主力损失不增加。
即使通过也只是新开发证据，不能认证专家；BC仍为0。

主agent资源空闲后可用以下PowerShell命令；不带`--execute`仅计划：

```powershell
wsl -d Ubuntu-22.04 -- env PYTHONDONTWRITEBYTECODE=1 /root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/human-tactics-positive-exchange-v2/launch.py --execute
```

launcher核验FROZEN_SOURCES并拒绝已有runs/train；每局冻结并逐步复核运行时、地图、
源码；全部完成后自动调用audit_native.py重算原始图选择、严格事件及真实永久伤亡。
超时/崩溃/缺终局/SHA变化即停止，保留无效数据，不计败局。进程清理沿用已有
serial runner独立进程组约束。没有改旧历史文件、冻结环境或主进展文件。
