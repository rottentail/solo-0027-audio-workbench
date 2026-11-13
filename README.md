# Audio Workbench

Python 标准库实现的 PCM 音频处理 HTTP 服务，提供素材检测、片段渲染与多轨混合。需要 Python 3.10 或更新版本，无第三方依赖。

## 启动

```sh
python3 -m audio_workbench.server --host 127.0.0.1 --port 8765
```

默认只监听本机；服务没有身份验证，勿直接暴露到不可信网络。没有环境变量配置。

## 接口

均为 JSON POST，`audio` 是完整 WAV 文件的 base64 编码。支持 16 位未压缩 PCM、单声道或立体声、8–48 kHz、最长 30 秒。请求体上限 8 MiB。

* `/inspect`: `{"audio":"..."}`，返回采样率、声道数、帧数、时长和归一化峰值。
* `/clip`: `{"audio":"...","start":0.1,"end":1.2,"gain":1.0}`，时间单位为秒，区间左闭右开，返回 `audio` 和 `properties`。
* `/mix`: `{"tracks":[{"audio":"...","offset":0,"gain":1}]}`，最多 8 轨；格式必须相同，偏移单位为秒，输出最长 30 秒。

增益范围为 0–4，混音结果饱和到 16 位范围。错误返回 HTTP 400 和 `{"error":"..."}`，未知路径返回 404。输出的 `audio` 可 base64 解码保存为 WAV。

## 验证与结构

```sh
python3 -m compileall -q audio_workbench
python3 -m audio_workbench.smoke inspect
python3 -m audio_workbench.smoke clip
python3 -m audio_workbench.smoke mix
```

`server.py` 负责 HTTP，`service.py` 编排和校验，`waveio.py` 读写音频，`processing.py` 处理样本；`smoke.py` 经真实 HTTP 路径执行有限检查。自动化测试套件有意延后，由后续工程任务补充单元测试和边界覆盖。

不提供视频解码、压缩音频格式、重采样或持久化；这些能力需要额外媒体依赖和设计。
