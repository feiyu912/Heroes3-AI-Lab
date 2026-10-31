# batch01 独立失败诊断

原始失败 RESULT 不变：6格完成准入，cell06 原生正常退出但严格原生审核失败，cell07未跑，整批无PPO更新。六个已准入局不构成完整平衡训练批，不能补两格拼批或据此汇总能力胜率。

cell06 Director 为player0，Nullkiller2为player1，seed2026102006。client.log 的rq291是对手 GarrisonHeroSwap、pack189；实际接收后出现 Cannot swap garrison hero 和 Got false，后来的 NativeRequestAck 却为player1/success1，且没有该ID的Director注册。审核拒绝行28617/28629为同一次失败的原始及系统消息镜像，并非两次非法操作。

独立读取 capsule03/source-snapshot 中 CGameHandler.cpp，以及当前未变的实际原生 NetPacksServer.cpp，两者均逐SHA核对 capsule03/build-source-manifest：NetPacksServer.cpp 的 visitGarrisonHeroSwap 将 garrisonSwap 返回值赋给result；CGameHandler.cpp 的精确投诉文本只在既没有驻军英雄、也没有访问英雄的else分支出现并returnfalse。普通处理分支虽按result记录Gotfalse，后面仍sendPackageResponse(true)。所以此处ACK success1只是该应答路径的成功字段，不能推翻实际apply=false。日志不足以证明NK为什么发出此请求，也不足以归因于Director或证明必然复现。不得改变NPC或放宽全局审核追认本局。

新完整8格重试须单独预注册并完整披露旧失败：旧6格不重用，T2/超参/奖励/模型/审核相同，只明确更换整块seed；同类失败再次出现即停下诊断，不能持续换seed直到成功。新seed不修复原生缺陷，因此“仅纳入没有触发原生失败的轨迹”是一个有效性条件，可能随策略/对手路径变化，并非可假定随机缺失。报告应保留每次尝试的计划格数、实际运行/准入/拒绝/未运行数和失败机制，不能将无效局算输，也不能静默从评估分母删除；固定独立DEV任何无效格都会限制该完整评估结论。新批即使通过，只证明该预注册批可训练，不证明温度提升能力，也不能掩盖旧批的运行可靠性失败。

本目录 AUDIT.json 和 review.py 仅作CPU只读诊断，不修改raw/旧审核/旧RESULT、不准入训练、不运行native/GPU。它绑定原始失败证据与精确编译源码SHA，而非签发成功整局证书。

