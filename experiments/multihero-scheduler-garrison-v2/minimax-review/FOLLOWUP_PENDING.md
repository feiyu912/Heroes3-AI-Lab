追加只读审核任务（待首轮服务返回后再实际派发；本文件本身不代表已调用）。

主实施代理报告了以下实测观察，我尚未向你附送原生日志，故必须将其标注为实施者报告，不能称你已核验原始证据：
- baseline/filtered 两组已构建成功，accepted 原字节恢复。
- baseline 实际 positive-MP garrison 建立，7资源/army/stock 守恒通过。
- baseline 仍 scheduler_selected hero3，发送 move，ACK result=1 但位置不变。
- baseline 第2回合 hero0 遇 hero2，触发原 original-unhandled exchange 回调，45秒超时；每hero每turn位移门未满足。
- filtered 依原计划只运行一次，尚未给你结果。当前两臂不得宣称资格通过。

请基于先前完整源码文本和上述明确标识的实施者报告，独立评估下一轮：
A 将 common setup 从 original-unhandled 切到已有 qualified close-only 候选，再做同一个 isGarrisoned filter 单因素；
B 保持 common candidate 代码，改用隔离地形避开两hero会面。
比较可识别性、分层资格、是否改动过多因素、可保留的原始证据、需要怎样预注册和单次原生运行。不要编造通过或声称你读过未提供的原日志。是否需要先补全close-only已资格化证据链？请列出必要条件，给明确推荐与理由。
