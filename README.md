# Audio Workbench

Python 音视频处理 HTTP 服务，提供 PCM 音频处理和持久化媒体转码任务。需要 Python 3.10 或更新版本，媒体引擎由 `imageio-ffmpeg` 提供。

## 启动

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m audio_workbench.server --host 127.0.0.1 --port 8765 --data-dir ./media-data
```

默认只监听本机；服务没有身份验证，勿直接暴露到不可信网络。`AUDIO_WORKBENCH_DATA` 可设置数据目录，`--data-dir` 优先；`--workers` 为 1–4，默认 2。一个数据目录只允许一个服务进程使用。

## 接口

均为 JSON POST，`audio` 是完整 WAV 文件的 base64 编码。支持 16 位未压缩 PCM、单声道或立体声、8–48 kHz、最长 30 秒。请求体上限 8 MiB。

* `/inspect`: `{"audio":"..."}`，返回采样率、声道数、帧数、时长和归一化峰值。
* `/clip`: `{"audio":"...","start":0.1,"end":1.2,"gain":1.0}`，时间单位为秒，区间左闭右开，返回 `audio` 和 `properties`。
* `/mix`: `{"tracks":[{"audio":"...","offset":0,"gain":1}]}`，最多 8 轨；默认格式必须相同，偏移单位为秒，输出最长 30 秒。可附加 `"format":{"sample_rate":48000,"channels":2}`，先对每轨做线性插值升采样与单、双声道转换；目标采样率不得低于任一源采样率。

增益范围为 0–4，混音结果饱和到 16 位范围。错误返回 HTTP 400 和 `{"error":"..."}`，未知路径返回 404。输出的 `audio` 可 base64 解码保存为 WAV。

### 持久化媒体任务

* `POST /jobs`: `{"source":"base64 媒体内容","preset":"mp4","start":0,"duration":5}`。`preset` 可选 `mp4`（H.264/AAC）或 `audio`（WAV），源文件最大 5 MiB，时长最多 60 秒；返回 HTTP 202 和任务对象。
* 时间线使用相同入口：`{"preset":"timeline","segments":[{"source":"base64 媒体内容","start":0,"duration":1}, {"source":"base64 媒体内容","start":2,"duration":1}]}`。每段需包含视频和音频，最多 8 段，总源数据不超过 5 MiB，总时长不超过 60 秒，单段不少于 1/30 秒。输出统一为 640×360、30 fps、48 kHz 双声道；画面按比例缩放并补黑边，片段不足时末帧和静音补齐。音轨或视频流缺失会使任务失败。
* `GET /jobs/{id}` 查询状态和错误；`GET /jobs/{id}/result` 在成功后返回 base64 的 `audio_video` 和 SHA-256。
* `POST /jobs/{id}/cancel` 请求取消，提交空 JSON 对象。排队任务立即取消，执行中的任务终止子进程后变为取消状态；已结束的任务无法取消。

任务和源文件保存在数据目录。进程重启后排队任务继续执行，原来执行中的任务标记为失败并清理临时结果；调用者可重新提交。产物先写入临时文件再保存，并在读取时校验摘要。服务不自动删除历史素材和产物，请在服务停止后自行维护数据目录。

## 验证与结构

```sh
python3 -m compileall -q audio_workbench
python3 -m audio_workbench.smoke inspect
python3 -m audio_workbench.smoke clip
python3 -m audio_workbench.smoke mix
python3 -m audio_workbench.job_smoke
```

`server.py` 负责 HTTP，`service.py` 编排和校验，`waveio.py` 读写音频，`processing.py` 处理样本，`jobs.py` 管理数据库和执行器；两个 smoke 模块经真实 HTTP 路径执行有限检查。自动化测试套件有意延后，由后续工程任务补充单元测试和边界覆盖。

不提供身份认证、媒体探测接口、自动重试、进度推送或分布式执行。
