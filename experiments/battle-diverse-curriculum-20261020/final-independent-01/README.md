# 最终独立CPU审核准备

只准备脚本，未把进行中的更新作为最终结果。audit_final.py在原RESULT未通过、30个record未齐、四份最终DEV报告未齐时退出2、不签发最终证书。脚本不会等待轮询或启动native/GPU；root在实际session69882结束后显式调用。

完整后审查：488个冻结输入当前SHA；全部30个真实checkpoint与rollout SHA/字节/完整边界/Adammoment载荷；逐参数独立复算每轮与相对B64的actor heads、critic heads、last graph变化，冻结层不得变化；最终model/Adam实际CPU恢复；240个真实case×role×opponent各64个transition，共60TRAIN图/15360行；真实terminal ±1还原、family/role/opponent/case终局频次、cuts和15次phase fragment计数；每轮末GAE next_value bootstrap。没有再演全批神经网络概率，也不声称独立CUDA恢复或live native恢复。

64DEV原JSON、日志镜像和真实shutdown、固定原作者公开CPU ONNX身份、map/seed/role/模型与输入SHA、合法/normal/胜负/损失以及逐对翻转全部核验；只有整局图摘要，不能伪造首次动作分叉/完整世界因果。统计报告先区分真实更新和独立收益，再根据TRAIN覆盖及终局频次解释局限，不将重复地图终局当独立泛化样本。

root完成后命令（out必须为新目录）：

```
wsl -- env PYTHONPATH=/root/heroes3-ai-lab/src/gym LD_LIBRARY_PATH=/root/heroes3-ai-lab/src/gym/vcmi/rel/bin:/root/heroes3-ai-lab/onnxruntime/lib /root/heroes3-ai-lab/venv/bin/python /mnt/g/Heroes3-AI-Lab/experiments/battle-diverse-curriculum-20261020/final-independent-01/audit_final.py --run /root/heroes3-ai-lab/evaluations/battle-diverse60-native-02 --out /mnt/g/Heroes3-AI-Lab/experiments/battle-diverse-curriculum-20261020/final-independent-01/actual-review-01
```

package.py --audit <通过的AUDIT.json> --out <新目录> 默认只生成完整证据包计划；root明确加--execute才复制全部来源/模型/rollout/原始评估至按SHA分层的新目录，每件逐SHA复核，不修改/删除原文件。没有通过最终独立审计不能生成认证包。保留未压缩原raw直到完整审核/归档完成，避免审计输入路径失效。
