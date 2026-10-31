# 原生 Ubuntu GNU11 工具链资格

独立 prefix 完成原4186普通文件（177088756字节）逐SHA及86个重基址链接核验，既有迁出、accepted、运行 profile 与系统安装未修改。实际程序为GCC/G++11.4.0、binutils2.38、Ninja1.10.1、CMake3.31.10；编译器 ELF 运行依赖全部可解析，程序运行使用宿主glibc，独立compiler-runtime仅提供旧非glibc工具依赖。

`attempt-02` 在 canonical GPU→pool 两把真实非阻塞锁、继承 FD 与 inode验证下，通过C与C++20真实编译、可执行链接及配对旧loader实际执行，输出C:42与CXX20:12。C++20含vector/ranges/thread。实际include及link trace严格复核都来自新sysroot，目标headers与crt/libstdc++/libgcc/libc未混入宿主开发文件。工具链证书在prefix/QUALIFIED_TOOLCHAIN.json，环境键在environment；构建必须沿用--sysroot和两个-B参数，不设GCC_EXEC_PREFIX。

`attempt-01` 保留工程失败：过度显式GCC_EXEC_PREFIX破坏G++自己的相对relocation查找，C成功而C++找不到iostream。移除该变量后同一prefix的已保存头文件即可通过，无需新增文件或降低编译闸门。两次总4个编译调用，3个成功可执行文件，1个预处理头查找失败；不是训练或能力进展。

**范围限制**：上述证书是核心编译工具资格，VCMI完整目标依赖闭包尚未资格化。43个旧target shared ELF中39个严格oldloader依赖闭包通过，SDL2及其image/mixer/ttf共4个不通过（缺传递库或宿主fallback版本冲突）。`target-closure-01/RESULT.json`明确failed；loader某些版本错误仍返回0，审计同时检查stderr与宿主fallback，不能只看returncode。`MISSING_TARGET_DEPENDENCIES.json`给出30个直接缺失SONAME、原dpkg包名/精确版本/Depends（包名映射基于已知SONAME，非单独验证文件归属），递归缺包仍需继续。此限制不推翻已验证的现有profile采用hostloader的四游戏回归。

拥有编译子进程正常退出，两次controller均进入finally释放本身资源锁；稍后的重新取得尝试遇到其他controller持锁，遵守nonblock退出，没有删除或替换锁文件，不声称此时全局资源空闲。未编译VCMI、未运行新游戏、未启动GPU训练、未更改模型或final test。
