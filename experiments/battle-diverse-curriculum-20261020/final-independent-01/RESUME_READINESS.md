# 保存与续训边界

当前30轮是真实完成的学习与逐轮保存，最终模型和Adam在独立CPU审核中真实加载。它不等于当前CLI已具备恢复续训资格。`support.validate_args`同时要求B64 SHA与`not a.resume`，因此最终update30输入及resume选项均被门禁拒绝；这是明确未支持，不能报告成本次实际触发的恢复错误。

未启用的继承resume分支恢复model（构造器）与Adam、Torch CPU/CUDA RNG，但遗漏保存的Python/NumPy RNG与累计optimizer hook counter。完成30轮后继承公式`phase=(previous+iteration)//2`从15开始，注册课程只有0..14。直接移除门禁不是修复。原生进程、正在进行的battle、step cursor未保存且标记`native_environment_restorable=False`，不能声称无缝恢复原战斗。

后续隔离版本的最小资格应为：同architecture与参数顺序完整恢复model/Adam，各参数moment和step逐项匹配；恢复全部四类RNG与累计真实hook步3840，environment_steps15360与update30；明确新的阶段注册、seed、source epoch和update31起始编号，不从B64/newAdam重置；模型初始delta相对父update30及B64分别保留。原生环境在预注册的新episode boundary重建，旧未完片段保留历史身份但不续接假状态。

必须先做非零后续更新的实际恢复验证：恢复瞬间状态/RNG读回一致，真实新onpolicy采样、Adam step递增、新原子保存与再次加载；不能用`--resume`标记或CPU静态通过替代。新DEV至少记录每步实际obs、合法候选、模型动作/概率、native返回与终局，可重算首次政策差异；目前旧DEV只有整局digest，不能追补不存在的逐步证据。

`READINESS_CPU_CHECKS.json`只认证静态源码和四个拒绝不完整最终结果的临时假fixture，0native/0GPU/0optimizer；它没有认证上述未来续训机制。
