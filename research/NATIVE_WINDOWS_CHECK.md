# Windows 原生构建尝试

日期：2026-10-13。目标：验证原生 Windows 路线的工具与具体阻碍；未启动训练，未完整构建或运行 VCMI/Gym。

## 结论

Windows 原生 C++ 工具链可用，已编译并运行 C++20 小程序。官方 VCMI 配置过程能识别编译器，但尚缺完整引擎依赖。固定版本 vcmi-gym 训练引擎还存在明确的平台移植阻碍，不能按现有源码直接用 MSVC 构建。

此结果不等于 Windows 无法做训练；它表明本项目选择原生路线还需要引擎依赖准备、训练入口移植、Python 扩展与多进程运行验证。为了最快获得战斗采样闭环，下一步推荐优先在现有 WSL2 验证匹配训练 fork；原生部署保留为后续目标。

## 实测结果

| 检查 | 结果 | 证据 |
|---|---|---|
| Visual Studio | 已安装于 D:\visual studio，Community 2026 | vswhere 查询 |
| 编译器 | MSVC 19.51.36244.0，x64 | smoke-configure.log |
| CMake/Ninja | Visual Studio 自带，CMake 4.2.3-msvc3 | cmake-version.log；smoke构建 |
| C++20 编译/链接/运行 | 全部通过，输出sum=10 | smoke-configure/build/run.log，results.json三项exit=0 |
| 训练入口POSIX头文件 | termios.h找不到，编译exit=2 | posix-headers.log |
| 训练入口系统分支 | 未定义MAC/UNIX时触发Unsupported OS，exit=2 | os-gate.log |
| 官方VCMI初次配置 | 编译器检测通过；Iconv未找到，exit=1 | upstream-configure.log |
| 指向现有Anaconda依赖后 | 找到Iconv/Zlib，下一阻碍为minizip/minizip-ng，exit=1 | upstream-prefix-configure.log、upstream-prefix-exit.txt |
| 现有源码完整性 | git status仍为空 | 本次检查，所有输出在research/native-check |

“未在PATH找到工具”不能解释为“机器没有安装工具”。本次定位了Visual Studio自带工具，无需先安装新的C++编译器。Conan/pybind11等未在当前Windows Python包环境发现；未安装或下载依赖。

## 检查的准确范围

训练入口两项编译检查使用的是最小复现片段，镜像固定训练fork `ML/MLClient.cpp` 的无条件 `termios.h`/`unistd.h` 引入和系统宏分支。不是声称已编译完整MLClient，也没有声称这两处是全部Windows不兼容项。`vcmi_gym/connectors/v15/threadconnector.cpp` 同样引入unistd.h，connector的模块后缀设置亦需检查。

源码依据：[训练引擎固定入口](https://github.com/smanolloff/vcmi/blob/e956242503f465ae6ec0a62a3aeb2c4ea179db5c/ML/MLClient.cpp)、[Gym connector构建](https://github.com/smanolloff/vcmi-gym/blob/11241d496db95541766498373e23245a67847a97/vcmi_gym/connectors/CMakeLists.txt)。源码原有版权/许可记录见research/evidence中的文件。

官方引擎配置关闭launcher/editor/tests/MMAI，仍需核心依赖。把Anaconda Library加入查找路径只是诊断：证明最初Iconv报错属于依赖查找问题，**不证明其全部库版本/ABI适合正式VCMI构建**。正式原生构建应使用统一锁定的依赖集，不继续随意混用系统库。

## 如何复现

Windows PowerShell运行 `G:\Heroes3-AI-Lab\research\native-check\run-check.ps1`，脚本会在当前进程加载VS开发环境，并执行基础工具链与平台阻碍检查。不会改系统PATH或游戏文件。脚本中的VS安装路径对应本机。

第二次依赖路径诊断在加载同一VS环境后使用VS自带CMake，对已有upstream-build配置增加 `CMAKE_PREFIX_PATH=D:/anaconda3/Library`；原始输出保留在upstream-prefix-configure.log。各子命令的exit code单独记录；脚本自身exit=0不代表所有检查通过。

## 后续两条路线

1. **最快验证训练：WSL2。** 先审计Linux已有依赖、匹配fork构建要求和下载规模，再做单战斗闭环。Windows原生游戏/未来模型部署仍可保留。
2. **坚持原生训练：平台移植专项。** 准备匹配引擎依赖，替换/条件化POSIX终端行为，补Windows DLL命名/导出与Python `.pyd` 加载，验证生命周期与spawn多进程，再测reset/step。工作量需进一步源码审计，不能承诺仅改两行即可完成。

本次没有大规模下载、包安装、模型训练或原版文件修改。尚未生成游戏可执行程序或可运行Gym环境，因此吞吐和并行数量仍未知。
