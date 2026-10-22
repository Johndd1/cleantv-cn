# 仓库结构与版本范围

目录组织参考用户提供的 CleanYourTV 仓库截图，保留本项目实际功能和上游许可。

- `launcher/` 是完整 Android Gradle 工程，应用模块为 `launcher/app/`，Kotlin 测试位于该模块的 `src/test/`。
- `tools/` 保留安装、恢复、设备检查与投屏辅助工具，命令均从仓库根目录执行。
- `tests/` 保留 Python 模拟设备测试。
- `docs/` 保留改动和验证记录。
- `examples/` 提供命令示例；`addons/` 与 `themes/` 明确当前扩展和主题能力边界。
- `local/` 继续位于仓库根目录，用于私有签名配置和设备恢复记录，禁止提交。Gradle 已调整为从该位置读取可选签名配置。

本次以 `48b9c9bd29402ac8ac659e78ab3097662a0b491a` 为基础整理目录，没有合入另一个工作区仍在修改的 Android 6 / Home 键接管修复。原有验证记录针对 `1.16-home.2-local`；不代表正在调试的版本已经真机验收。目录调整的验证记录见 `STRUCTURE-VALIDATION.md`。
