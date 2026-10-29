# Windows 独立桌面入口

这是可选的 WinForms + WebView2 窗口。默认仍可使用浏览器；只有使用者需要桌面软件时才启用。

1. 已确认的 profile 加入 `desktop_windows: true`、`workbench_name` 和可选 `port`（默认 8932），再运行 bootstrap。不同工作台应使用不同端口。
2. 在生成的工作台运行 `powershell -NoProfile -ExecutionPolicy Bypass -File app/windows/build.ps1`。需要 Windows x64、.NET Framework 4.8 编译器、Python 3.10+ 和已安装的 Microsoft Edge WebView2 Runtime。
3. 构建脚本从官方 NuGet 下载固定版本 SDK，先核对 SHA-256，再提取并编译。依赖版本、来源和哈希见 `dependencies.json`；不附带编译产物或个人资料。
4. 运行 `powershell -NoProfile -ExecutionPolicy Bypass -File app/windows/install-shortcuts.ps1` 创建桌面入口。它拒绝覆盖其他目标的同名快捷方式。
5. 从桌面打开后，使用 Windows 菜单固定到任务栏。关闭窗口后，再从固定图标重开，确认仍是独立窗口。任务栏与程序的应用身份按工作台目录生成，不能固定浏览器代替。

窗口打开时启动本地 Python 服务，每 10 秒检查连接并在断开后恢复；关闭时结束自己启动的服务。它不扫描照片、不设计划任务、不执行筛选，不会变成持续运行的整理机制。

交付前在使用者实际机器检查：打开、关闭、从固定入口重开、服务中断后恢复、照片预览、保存审核意见后重开仍在。下载失败应检查网络和 TLS，不能关闭证书或哈希校验。换目录后应重新生成快捷方式。浏览器方式的安装不需要编译器；桌面方式需要上述构建环境。
