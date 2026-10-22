# 1.16-home.2-local 验证记录

日期：2026-10-22。此版本为预发布，未连接或改动电视，尚无遥控器操作、型号适配、重启/待机接管与媒体播放的真机验收。

## 已完成

- `assembleStandardRelease`：构建成功。
- `testStandardReleaseUnitTest`：3 项 Kotlin 测试通过，验证首页包名配置、顺序及数量边界。
- `python3 -m unittest discover -s tests -v`：15 项测试通过，设备使用有状态模拟对象，未使用真实电视。
- `lintStandardRelease`：0 个错误，54 个警告；不代表已修复全部 lint 警告。
- `bash -n tools/install.sh tools/restore.sh`：语法检查通过。
- APK manifest 包名经独立安装工具与 `aapt2` 交叉核对，签名经 `apksigner verify` 核验。

## APK 信息

| 项目 | 值 |
| --- | --- |
| 包名 | `app.orchard.tv` |
| versionName / versionCode | `1.16-home.2-local` / `20` |
| 最低 / 目标 / 编译 SDK | 21 / 34 / 36 |
| APK 字节数 | 2,373,988 |
| SHA-256 | `2ad62bd8691d5bd1cbb2076f39cef612d66d0a9cbbf95f6004d84a9f9df851b3` |
| 签名 | 本地 Android debug key；v1 / v2 校验通过 |
| 签名证书 SHA-256 | `97556a47ef5abede73838441c71f1e3716083a7ecee35ce8308e077329f396cc` |

不能直接覆盖原作者或上游的不同签名版本。安装工具不会为处理签名冲突自动卸载已有应用。

## 仍需验证

- 电视是否允许安装、授权和桌面切换。
- 遥控器长按菜单、焦点、首页配置及隐藏应用恢复的实际操作。
- Home 键、重启、待机唤醒、HDMI 切换与原厂功能是否正常。
- 投屏、硬盘和常用视频应用是否能完成实际播放。
- 对应电视上按恢复记录还原原桌面与权限是否成功。

原版截图与兼容性报告已在 README 中标明来源，不能替代本版验收。
