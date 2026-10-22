# 目录调整验证

日期：2026-10-22。基线：`48b9c9bd29402ac8ac659e78ab3097662a0b491a`，版本 `1.16-home.2-local`。

- Python 模拟设备测试：15 项通过。
- Kotlin 首页配置测试：3 项通过。
- Android `assembleStandardRelease`：在迁移后的 `launcher/` 工程构建成功。
- `lintStandardRelease`：0 个错误，47 个警告；未把警告当作已修复。
- `bash -n tools/install.sh tools/restore.sh`：通过。
- Markdown 相对链接与仓库目录检查：通过。
- 安装脚本的自动构建和 APK 路径已更新到 `launcher/`；本次未执行电视安装或恢复。
- 私有设备记录、签名配置、密钥、APK 和构建缓存均未纳入提交。

本次验证针对目录调整，不构成真机接管验收；另一个本地工作区中的 Android 6 / Home 键修复未并入。
