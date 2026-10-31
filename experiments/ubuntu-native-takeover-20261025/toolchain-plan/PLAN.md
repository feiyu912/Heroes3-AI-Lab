# 原生 Ubuntu C++ 工具链：只读调查及最小适配方案

当前无需因此阻塞运行 profile 的恢复。方案完成后，根代理另授权在临时原盘清理前提取不足2GiB的必要编译输入；已实际完成`../toolchain-inputs`，4,186普通文件、177,088,756字节、85条原链接目标全部双reader+落盘校验通过。**未下载或安装系统包、未执行编译、未修改 accepted build / 冻结 battle**。

## 现场结果

当前系统是 Ubuntu **26.04.1**；PATH 没有 gcc/g++/clang/cmake/ninja/make。`dpkg-deb`、`pkg-config`、`ar`、`ld`、`readelf`存在，但系统binutils为2.46、libc为2.43、libstdc++为16，不等同于旧WSL构建工具链。Boost、SDL2、TBB、LuaJIT、minizip等开发头也没有安装。

正确原盘复核后的旧 `CMakeCache.txt` 和 `CMakeCXXCompiler.cmake` 指定 GNU **11.4.0**、CMake **3.31.10**、Release `-O3 -DNDEBUG -std=gnu++20`，PCH ON、LTO OFF。真实 DirectorAI 编译命令还含 hidden visibility、PIC、function/data sections、`-fno-semantic-interposition`，完整flags/defines已保存于`TOOLCHAIN_SOURCE_PLAN.json`，不能只根据“gcc11/Release”口头重建。

旧构建没有 `compile_commands.json`，其cache的导出开关为空。已从**正确**`.ninja_deps`按v4记录长度与node-ID校验和解析6,302条路径、810条依赖记录，得到3,799个实际用过的系统header路径。`ACTUAL_COMPILED_SYSTEM_HEADERS.json`记录这些路径，`prepare_plan.py`可重现解析；不能把最初`strings`扫描得到的带二进制尾字符名称当header真名。

旧战略build现有788普通文件、**3,402,718,593字节**，含707个`.o`、13个`.gch`。早期清理不意味着现存所有PCH都不存在；后来的重编译已留下这些文件。它们的正确字节已经过全源复核，但尚未证明迁移后可直接复用。

## 推荐：用户目录内恢复旧GNU11与有界sysroot

不用sudo，也不动系统Python或系统库。新的工具链prefix应独立于旧迁出树、已验证profile、accepted source/build，例如由根代理确定的`/home/kaicheng/Heroes3-toolchain-gcc11-01`。从已完整恢复并SHA确认的`source.vhdx`定向读取下列清单，仍使用已修正的两个payload reader逐项比较；目录和链接也须检查，不沿用有缺陷迁移reader的摘要。

`TOOLCHAIN_SOURCE_PLAN.json`已列出原inode、字节数、mode及链接目标，元数据全部有对应记录、无缺项；后续`toolchain-inputs/AUDIT.json`已对这些原源输入的字节完成双reader与readback验证：

| 分组 | 普通文件 | 源字节 |
|---|---:|---:|
| 既有编译真实用过的headers | 3,799 | 26,746,783 |
| GCC11内部程序、builtin headers及链接支持 | 166 | 101,585,711 |
| GCC/binutils/Ninja程序入口的实际文件 | 17 | 6,990,008 |
| 原依赖CMake/pkg-config元数据 | 149 | 91,857 |
| 直接链接库、crt和编译器依赖家族 | 55 | 41,674,397 |
| **本轮最小保留集** | **4,186** | **177,088,756** |

另有85条原链接目标已经核验并保存，**未实际建立链接或运行工具链**。初稿155.7MB遗漏GCC目录中的开发`.so`链接及8个目标，已在实际提取前修正；初稿保留于`pre-gcc-link-closure/`。该177.1MB不是已通过的完整ELF依赖闭包。组装工具链后用`readelf -d`读取compiler、cc1plus、collect2、binutils、Ninja、目标库的`DT_NEEDED`，定向补齐缺失的传递库；CMake配置若要求额外原header，则只补对应同版原文件并记录，不混入26.04开发头。

CMake分发本身已经在主lab的已复核文件中：`python-packages/cmake`，3,804文件、67,368,989字节。优先使用新coherent profile的这一份；它尚未在本调查里执行。ONNX Runtime头/库也复用正确profile，不另换版本。

工具链建议布局：

```text
user-prefix/
  sysroot/usr/bin/{gcc-11,g++-11,cpp-11,ninja,...}
  sysroot/usr/lib/gcc/x86_64-linux-gnu/11/{cc1,cc1plus,collect2,...}
  sysroot/usr/include/{c++/11,boost,SDL2,...}
  sysroot/usr/lib/x86_64-linux-gnu/{crt*.o,*.so,cmake,pkgconfig,...}
  compiler-runtime/     # 仅工具程序实际缺失的非glibc依赖
  QUALIFIED_TOOLCHAIN.json
```

不能把整个旧sysroot的`usr/lib`塞进宿主进程的`LD_LIBRARY_PATH`：那可能把旧libc和当前宿主loader混装。编译器程序先在干净的显式环境中定位依赖，仅对实际缺失的libmpc/libmpfr/libisl等提供独立`compiler-runtime`；目标编译/链接通过`--sysroot`使用旧headers、crt和链接库。必要时提供prefix内`-B`/`GCC_EXEC_PREFIX`/`COMPILER_PATH`，以真实`-print-search-dirs`和`-v -E`结果证明cc1、as、ld、headers均取自指定prefix，而不是假设GCC可搬移。

系统`pkg-config`可以作为发现工具，但必须只在这个进程设`PKG_CONFIG_SYSROOT_DIR`、`PKG_CONFIG_LIBDIR`，避免发现当前系统开发库。新CMake配置应显式设置sysroot、原GNU11编译器/binutils/Ninja、Boost/TBB和profile ONNX路径。`ubuntu22-gcc11.cmake.in`是待使用模板，缺少独立工具链通过证书时明确停止；没有把编译器测试改为仅静态归档来绕过真实链接。

原盘方案不需要下载。如果某必要包确实不在原盘，再用官方Ubuntu **Jammy同版**deb，校验对应签名仓库索引和包SHA后仅`dpkg-deb -x`到用户prefix；不`dpkg -i`，不把26.04仓库默认gcc作为“同工具链”。准确原包版本和Depends已从迁移保存的dpkg状态记录提取到`ORIGINAL_PACKAGE_SET.json`：gcc/g++/cpp11为`11.4.0-1ubuntu1~22.04.3`，binutils为`2.38-4ubuntu2.12`，Ninja为`1.10.1-1`，libc6-dev为`2.35-0ubuntu3.15`，另含Boost1.74/SDL2/LuaJIT/TBB等原依赖。此清单不是当前网络可下载性保证。

## 原objects复用与全新构建

**不能直接在旧accepted build调用cmake/ninja。** cache、rules.ninja、PCH命令、install常量、依赖日志均嵌有旧`/root/...`和`/usr/...`路径；实际profile路径、headers和mtime已不同。复制出来的旧Ninja图仍会尝试在旧位置重生成CMake；仅替换程序PATH不足以解决。

旧707个对象有潜在的局部重链接价值，且LTO关闭降低了对编译器插件的耦合，但正确SHA不等于迁移后重用资格。若以后做短路径，须在**新的复制build**中单独证明完整输入/宏/flags/ABI闭包、重建PCH、准确重基址命令，并做baseline对旧合格capsule的完整回归；不能混用不明旧对象来跳过公平对照。不会对旧cache做原地`sed`，不建立系统全局`/root`别名。

推荐先完成一个新build的配置及真实compiler/link/header试验；然后在相同工具链、相同flags、同一个固定scratch source/build/install前缀下，顺序构建baseline和candidate，再分别封存独立capsule，避免编译路径常量也变成处理因素。二者都从同一正确schema6原生源epoch起步，candidate只加入所登记的refill候选变化；不同时吸收调度或奖励改变。

正式pair可复用第一次已合格新build中的不变对象，但必须保留构建图/依赖与修改列表，并为两臂重建DirectorAI与关联链接目标。使用`vcmi` facade以及client/server所需目标完整产物，不能假装AI是独立可随意替换的动态插件：DirectorAI是OBJECT目标，最终链接进`libvcmi.so`。

全新build每臂最多按既有707个TU及13个PCH规划，已存build约3.4GB只作磁盘参照；没有墙钟或峰值RAM实测，不能报预计必在几分钟完成。两臂加临时链接/PCH建议预留至少20GiB空间。初始`-j2`测量RSS/可用内存/swap，再依测量调整；28逻辑CPU不等于28并发资格。真正编译阶段仍用canonical **GPU锁→pool锁**，不与GPU learner或重CPU诊断重叠，保存实际资源峰值；不因工具链适配降低原实验资源门。

## 下一阶段准入

1. 已完成必要原源输入的定向提取与双reader/path/inode/mode/大小/SHA/readback验证，证书见`toolchain-inputs/AUDIT.json`。仍须组装独立prefix、按已记录原目标在prefix内重建链接、检查必要ELF闭包，保持旧源不动。
2. 新prefix里的cmake/Ninja/GCC版本、程序依赖、实际include/link搜索路径和C/C++20编译链接探针通过；当前仍为零编译。
3. 新baseline构建/资源稳定性及原生回归通过，明确新构建epoch；之后才构建仅一个源码差异的candidate。
4. 原生机制fixture检验新增回城候选的真实路径/库存/容量资格及实际ACK状态守恒；这不等于学会招募或胜率提升。
5. 登记固定TRAIN校准与后续独立能力评估，不把工具链迁移或校准当PPO进展，final test继续封存。
