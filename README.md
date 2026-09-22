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


## YouTube 中文官方影视

`youtube-channels.json` 维护已核实的官方频道，`youtube.json` 保存公开视频元数据。每日任务读取频道近期长视频（至少 10 分钟，排除明显预告和花絮），按明确的《片名》归组，逐日累积，最多保留 3000 条。初次接入不是完整历史片库。频道读取失败保留原目录，最新页缺失不代表下架。上映年份未知时留空，不把上传年份当上映年份。

当前：央视电视剧、爱奇艺、爱奇艺大电影、腾讯视频。播放交给 App 内 YouTube 官方嵌入播放器，不保存媒体流地址；是否允许嵌入、登录和地区限制由 YouTube 决定。

## 新增直播订阅（2026-09-23）

新增 [Free-TV/IPTV](https://github.com/Free-TV/IPTV) 的澳洲、中国及香港列表，以及 [iptv-org/iptv](https://github.com/iptv-org/iptv) 的澳洲、香港及台湾列表；原有中国列表保留。直播订阅由 `additionalSources` 维护，在现有源后追加，避免改变原有源序号。每日生成配置时保留这些条目。

只引用上游播放列表，不复制其代码或宣称其内容属于本仓库许可证。IPTV-org 使用 Unlicense；Free-TV/IPTV 未声明仓库许可证。频道和台标权利归各自权利人。

本次在澳洲网络用客户端相同的 HLS/视频分片探测抽查 28 条线路，13 条通过；这是抽样结果，不代表全部可播放。新增六份列表合计 134 个 HTTPS 条目，含重复及地区限制频道，不等于新增可播放频道数。客户端继续验证播放分片、过滤失败线路并合并重复节目。Free-TV 台湾列表主要是 YouTube 页面，不符合当前 M3U 直播路径，未添加。
