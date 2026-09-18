# ZhuijuSources

追剧 App 的独立片源配置仓库。只提供接口地址与元数据，不托管影片。

订阅地址：https://raw.githubusercontent.com/jpocket8/ZhuijuSources/main/sources.json

## 自动更新

片源通过 GitHub Actions 每天自动更新。

GitHub Actions 每天 UTC 23:17（北京时间次日 07:17、布里斯班次日 09:17）运行；GitHub 调度可能延迟。也可在 Actions → Update sources → Run workflow 手动更新。

任务读取 awesome-zhuiju-free 最新目录，按稳定 ID 找到老刘备、小马的配置地址，再提取 HTTPS 标准 JSON（type=1）接口。去重后生成 sources.json。不执行 JS/JAR 插件；暂不兼容的资源不会自动成为可用片源。同步成功不等于所有影片均能播放。

任一上游获取或解析失败时，任务失败并保留上一版 sources.json，避免空配置覆盖。Git 历史可回退。需关注 Actions 失败通知。

settings.json 的 pinned 是置顶保留片源与已知功能限制，disabledUrls 可禁用地址，upstreams 指定已适配的上游 ID。sources.json 是生成文件，不应直接维护。

App 距上次成功更新满 4 小时自动获取配置，在前台定期检查，重新打开时补查；验证通过才替换本地缓存。网络失败时使用缓存或内置片源。旧版 App 需先安装支持订阅的新 APK。

## 本地运行

Python 3.12+，无需第三方依赖：

```sh
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/update_sources.py
```

## 来源与许可

目录来源：[laoma2053/awesome-zhuiju-free](https://github.com/laoma2053/awesome-zhuiju-free)，作者 laoma2053 及贡献者，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。这里选取部分入口、提取标准接口并添加 App 元数据；上游未对本应用背书。第三方接口与内容的权利仍属于各自权利人。
