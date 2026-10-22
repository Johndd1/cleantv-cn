# Android 桌面应用

需要 JDK 17、Android SDK 36，并配置 `JAVA_HOME` 与 `ANDROID_HOME`。

在本目录执行：

```sh
./gradlew testStandardReleaseUnitTest assembleStandardRelease lintStandardRelease
```

APK 输出为 `app/build/outputs/apk/standard/release/app-standard-release.apk`。

可选签名配置位于仓库根目录的 `local/signing.properties`；没有配置时使用本机 debug key。设备恢复记录也保存在仓库根目录的 `local/`，禁止提交。安装与恢复工具仍从仓库根目录运行，详见 [项目说明](../README.md)。
