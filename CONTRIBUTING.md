# 参与开发

Android 应用在 `launcher/`；设备脚本与 Python 测试位于根目录 `tools/` 和 `tests/`。提交改动时说明行为变化和验证结果。兼容性结论必须标明实测型号与系统版本。

```sh
python3 -m unittest discover -s tests -v
bash -n tools/install.sh tools/restore.sh
(cd launcher && ./gradlew testStandardReleaseUnitTest assembleStandardRelease lintStandardRelease)
```

不要提交 `local/`、设备地址与标识、家庭截图、签名密钥、密码、令牌或构建缓存。保留原有 MIT / OFL 许可与来源说明。
