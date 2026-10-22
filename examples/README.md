# 安装与恢复示例

在仓库根目录执行。需自行准备 adb、Python 3 和 APK；用电视实际地址替换占位符。

```sh
TV='<电视IP>' python3 tools/device.py check
TV='<电视IP>' APK_FILE='/absolute/path/cleantv-cn-standard.apk' bash tools/install.sh --preview
TV='<电视IP>' APK_FILE='/absolute/path/cleantv-cn-standard.apk' bash tools/install.sh --launcher-only
TV='<电视IP>' APK_FILE='/absolute/path/cleantv-cn-standard.apk' bash tools/install.sh
TV='<电视IP>' bash tools/restore.sh --preview
TV='<电视IP>' bash tools/restore.sh
```

先试用并核对设备兼容性，再设置接管。恢复依赖 `local/recovery/` 的原始记录。完整权限、签名和恢复边界见根目录 README。
