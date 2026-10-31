# 冒险对局构建复核：建议执行隔离非ML构建

2026-10-18。此补充只读核对源代码和现有ELF依赖，不启动编译/游戏、不改冻结原生库。WorkBuddy继续负责实施，避免两个窗口重复构建。

## 结论

建议按方案B建立独立的ENABLE_ML=OFF完整冒险运行环境。隔离编译属于已要求推进战略闭环的常规、可逆工程步骤，不应仅因为可能需要20–40分钟再阻塞等待用户确认。若出现新的磁盘/内存不足、缺少合法资源或权限限制，按实际原因处理，不绕过策略。

## 本次实际核对

- `/root/heroes3-ai-lab/src/gym/vcmi/CMakeLists.txt:119` 确实定义 `option(ENABLE_ML ... OFF)`，当前冻结rel/CMakeCache.txt为ON。
- server/CMakeLists.txt在ENABLE_ML分支添加并链接mlserverplugin。
- 对现有rel/bin/vcmiserver实际执行readelf，DT_NEEDED包含libmlserverplugin.so及libvcmi.so，RUNPATH指向旧rel/bin。
- lib/StartInfo.h:155为 `ML(ML::Config mlconfig)`，说明ML开关会影响共享类型，不能假设开启与关闭ML的客户端、服务端及库任意混搭兼容。

## 必须纠正的表述

现有插件是**构建时强制链接、运行时动态加载的共享库依赖**，不是静态链接。关游戏模组无法删除程序的DT_NEEDED依赖，这一工程判断正确，但术语应改正。当前statMode真正经StartInfo.mlconfig传递；不要继续把settings schema当已证明的根因，更不能由此推断战斗阵型参数“从来没传到服务端”。

源码有完整对局CLI、游戏状态初始化成功，支持“存在完整对局入口”，但不等于当前运行版本已经实际完成过完整对局。当前M0与M1边界应保留。

## 隔离构建实施要求

1. 新建冒险专用源码worktree/构建/安装或运行前缀；不得在冻结rel执行ninja，不覆盖既有.so/二进制。先确认实际Git仓库和磁盘空间。
2. 在独立目录配置ENABLE_ML=OFF，并使用相同源码/编译选项构建配套vcmiclient、vcmiserver、libvcmi及所需战略/战斗AI模块。不要只替换一个server再配旧ENABLE_ML=ON客户端/库。
3. 显式限定进程使用的新二进制和库路径；避免旧RUNPATH、LD_LIBRARY_PATH、服务端发现路径或AI目录把旧ML库混回新环境。用readelf/实际加载记录核对，而不是只看cmake命令写了OFF。
4. 复用合法游戏资产，用户配置/存档/日志/地图使用独立worker目录。不要随意删共享目录或覆盖另一个窗口的文件。复制配置时注意JSONC与真实配置通道。
5. 编译并发按当前可用内存和其他窗口负载选择，不默认开满28线程。保存源码版本、完整CMakeCache/命令/编译日志和依赖清单。
6. 编译前后核查冻结战斗关键库/二进制SHA未改变；新环境另立清单。对新构建失败做日志留档，不让失败破坏旧战斗复现。

## 实测顺序

先验证核心英雄派生地图在新环境加载，然后记录真实回合/天数推进、原生AI行动、存档和最终原生胜负，达到M1。只有初始化日志不够；时间到被timeout终止也不是完成对局。现有地图虽可加载，仍是开局接触的战斗模板派生，不能自动认定它适合探索/经济/扩张评估。

M1原生对局跑通后再推进自研战略接管、结构化整局轨迹和同图同种子基线；清楚标明Nullkiller2是原生AI。对新ML=OFF运行环境不能直接宣称现有MMAI/gym模型已可接入；若要复用，需要独立验证的战斗适配，不得把关闭整个ML运行时说成同时保留原训练接口。

长期仍按WORKBUDDY_NEXT_TASK_STRATEGY.md推进，不为了构建重新回到只刷单场胜率。
