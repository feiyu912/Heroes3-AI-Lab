# 同版工具链依赖补充及最终闭包

最终证书为独立 prefix 的 `TARGET_DEPENDENCY_CLOSURE.json`，SHA256 **d716b5712fd774c70924b6a44a8d0aff040b98bf7b145e9b232a8452811d84b3**。`target-closure-06/RESULT.json` 对138个共享ELF逐一实际调用配对旧loader（禁用cache），全部依赖解析通过，stderr为空、没有宿主库fallback、没有缺失SONAME。证书files路径相对toolchainroot，4279个普通文件SHA；links单列168个链接目标。此为构建依赖资格，不是游戏能力资格。

补充来源为73个原Ubuntu Jammy精确版本官方包。每个包均重新核验签名InRelease、Packages.xz大小及SHA、包元数据与deb大小/SHA，以及dpkg control。源包仅在用户目录解析，未系统安装。原4186已保存输入与prefix内4186文件最终SHA一致；3173个与同版Boost包内容重叠的现有文件逐bytes相同，全部未覆盖。Boost仅加入缺失BoostDetectToolset-1.74.0.cmake；未注入完整Boost头包。

累计新增175项：93普通文件32,737,442字节、82链接。提取策略保留所需包中的共享库和SONAME链接，因此也包含同包旁支共享库。最后只读可达性检查显示：原始46个共享ELF为根可达117个；其余21个属于已认证同版包内旁支（例如OpenSSL engines、glib gio/gthread、opusurl）。这些旁支亦全部通过独立闭包审计。它们不是新代码、flags或实验处理因素；两臂使用相同完整冻结prefix。不能把该集合称为绝对最小依赖集。

原版liblzma5 5.2.5-2ubuntu1.1不在当前普通索引，原23包报告实际22成功、1 found=false，未将22说成23资格通过。最终从Ubuntu官方20261001快照独立签名索引与SHA核验得到精确版本，未换新版本。snapshot包SHA为af77f099e7fa95a31267023535832804382fa66572a6b38002187be6e15116cb。

失败与重试均保留：supplement-01索引glob过宽导致核验早停；supplement-03因发现liblzma未取得而严格早停；两者均未更改prefix。后续每轮新缺来自真实ELF；libmd加入前target-closure-05记录实际缺libmd。其余成功补充manifest位于supplement-02/04/05/06/07。

root已在最终证书通过后启动baseline构建。随后的旁支可达性分析仅为只读：**没有实施prune，没有再次更改prefix，d716b证书完整保持不变**。冻结构建期间不得调整此epoch；无需为删除认证旁支打断公平两臂构建。

本子任务未编译VCMI、未运行游戏、未启动GPU学习器、未更新模型或触碰final test；后续baseline构建属于root/pair_builder的独立实际记录。
