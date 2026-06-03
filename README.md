# translator-server

一个基于 FastAPI 的翻译服务。默认使用 `fastText` 进行语种识别，并使用本地 `M2M100` 模型完成文本翻译；也可以切换到 OpenAI 兼容接口。

适合下面这类场景：

- 需要统一的 HTTP 翻译接口
- 希望完全使用本地模型，不依赖在线推理
- 需要在内网、离线环境或受控环境中部署

## Highlights

- Auto-detect 源语言，也支持手动指定 `source_lang`
- 默认使用本地模型推理，也可以通过环境变量切换到 OpenAI 兼容接口
- 基于 `uv` 管理 Python 环境与依赖
- 内置 Basic Auth
- 支持 Docker 构建和离线分发

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [API](#api)
- [Docker](#docker)
- [FAQ](#faq)

## Quick Start

### 1. Prepare models

确保本地已有以下模型文件：

```text
models/
├─ lid.176.bin
└─ m2m100_418M/
```

如果仓库使用了子模块，建议首次克隆时直接拉取：

```bash
git clone --recurse-submodules <your-repo-url>
cd translator-server
git lfs install
git submodule update --init --recursive
```

### 2. Install dependencies

```bash
uv python pin 3.12.13
uv sync
uv pip install -r requirements.cpu.txt
```

### 3. Run the service

```bash
uv run translator-server
```

默认监听：

- Host: `0.0.0.0`
- Port: `8191`

Windows 开发环境也可以直接运行：

```bat
run_service.bat
```

### 4. Test the API

健康检查：

```bash
curl -u admin:Admin@123 http://127.0.0.1:8191/healthz
```

翻译请求：

```bash
curl -u admin:Admin@123 \
  -H "Content-Type: application/json" \
  -X POST http://127.0.0.1:8191/api/v1/translate \
  -d "{\"text\":\"Hello world\",\"target_lang\":\"zh\"}"
```

## Project Structure

```text
.
├─ models/
│  ├─ lid.176.bin
│  └─ m2m100_418M/
├─ src/translator_server/
│  ├─ app.py
│  ├─ config.py
│  ├─ exceptions.py
│  ├─ main.py
│  ├─ schemas.py
│  ├─ security.py
│  └─ services/
├─ Dockerfile
├─ docker-compose.yml
├─ pyproject.toml
├─ requirements.cpu.txt
├─ requirements.cuda.txt
└─ README.md
```

## Configuration

### Runtime requirements

- Python `3.12.13`
- `uv`
- `Git`
- `Git LFS`

### Environment variables

| Variable | Default              | Description |
| --- |----------------------| --- |
| `APP_NAME` | `translator-server`  | 应用名称 |
| `APP_ENV` | `dev`                | 运行环境 |
| `LOG_LEVEL` | `INFO`               | 控制台日志级别，可选 `DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL` |
| `APP_HOST` | `0.0.0.0`            | 监听地址 |
| `APP_PORT` | `8191`               | 监听端口 |
| `LID_MODEL_PATH` | `models/lid.176.bin` | fastText 语种识别模型路径 |
| `TRANSLATION_MODEL_PATH` | `models/m2m100_418M` | 翻译模型目录 |
| `DEFAULT_TARGET_LANG` | `zh`                 | 默认目标语言 |
| `MAX_BATCH_SIZE` | `8`                  | 批处理大小 |
| `MAX_INPUT_CHARS` | `20000`              | 单次请求最大字符数 |
| `SEGMENT_MAX_CHARS` | `400`                | 单段最大字符数 |
| `MAX_LENGTH` | `512`                | 生成最大长度 |
| `MAX_NEW_TOKENS` | `512`                | 最大新增 token 数 |
| `TRANSLATION_DEVICE` | `auto`               | 推理设备，`auto` 会优先使用可用 CUDA，否则回退 CPU；也可显式设置为 `cpu` 或 `cuda` |
| `NUM_BEAMS` | `1`                  | Beam search 参数 |
| `M2M100` | `true`               | 是否使用本地 fastText + M2M100；设置为 `false` 时使用 OpenAI 兼容接口 |
| `OPENAI_API_KEY` | -                    | OpenAI API Key，仅在 `M2M100=false` 时必填 |
| `OPENAI_BASE_URL` | 官方默认地址               | 可选的 OpenAI 兼容接口地址，仅在 `M2M100=false` 时使用 |
| `OPENAI_MODEL` | -                    | OpenAI 模型名称，仅在 `M2M100=false` 时必填 |
| `BASIC_AUTH_USERNAME` | `admin`              | Basic Auth 用户名 |
| `BASIC_AUTH_PASSWORD` | `Admin@123`          | Basic Auth 密码 |
| `TRANSLATE_MAX_CONCURRENCY` | `5`                  | 翻译接口最大并发执行数 |
| `TRANSLATE_QUEUE_SIZE` | `20`                 | 翻译接口最大等待队列长度 |
| `TRANSLATE_QUEUE_TIMEOUT_SECONDS` | `30`                 | 翻译请求最长排队等待秒数，超时返回 `429` |

生产环境建议至少覆盖以下变量：

```bash
APP_ENV=prod
BASIC_AUTH_USERNAME=your-user
BASIC_AUTH_PASSWORD=your-password
```

如需使用 OpenAI 兼容接口：

```bash
M2M100=false
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=your-model
# 可选：使用兼容服务时配置
OPENAI_BASE_URL=https://example.com/v1
```

`M2M100=true` 时不会初始化 OpenAI 客户端，也不要求配置任何 `OPENAI_*` 环境变量。

## API

所有接口均启用 Basic Auth。

默认凭据：

- Username: `admin`
- Password: `Admin@123`

### `GET /healthz`

请求：

```http
GET /healthz
Authorization: Basic <base64(username:password)>
```

响应示例：

```json
{
  "status": "ok",
  "app_name": "translator-server",
  "model_name": "m2m100_418M"
}
```

### `POST /api/v1/translate`

请求：

```http
POST /api/v1/translate
Content-Type: application/json
Authorization: Basic <base64(username:password)>
```

请求体示例：

```json
{
  "text": "Hello world",
  "target_lang": "zh"
}
```

手动指定源语言：

```json
{
  "text": "Hello world",
  "source_lang": "en",
  "target_lang": "zh"
}
```

响应示例：

```json
{
  "translated_text": "你好，世界",
  "detected_source_lang": "en",
  "source_lang": "en",
  "target_lang": "zh",
  "model_name": "m2m100_418M",
  "device": "cuda",
  "took_ms": 218
}
```

## Docker

当前 Docker 部署使用多阶段构建：

- Builder 阶段安装 `uv` 和项目依赖
- Runtime 阶段仅保留运行服务所需内容
- 镜像内包含本地 `models/` 目录

### Build

```bash
docker build -t translator-server:latest .
```

### Run

```bash
docker run -d \
  --name translator-server \
  --restart always \
  -p 8191:8191 \
  translator-server:latest
```

### Compose

```bash
docker compose up -d --build
```

### Offline delivery

导出镜像：

```bash
docker save -o translator-server.tar translator-server:latest
```

导入镜像：

```bash
docker load -i translator-server.tar
```

## GPU Support

项目保留 CPU 与 CUDA 两个 PyTorch 安装入口：

```bash
uv pip install -r requirements.cpu.txt
```

默认启动脚本和 Dockerfile 安装 CUDA 12.8 版 PyTorch：

```bash
uv pip install -r requirements.cuda.txt
```

CUDA 版 PyTorch 在没有可用 CUDA 设备时仍可走 CPU；服务默认使用 `TRANSLATION_DEVICE=auto` 自动选择：

- `torch.cuda.is_available()` 为 `true` 时使用 `cuda`
- 否则使用 `cpu`

如需强制使用某个设备：

```bash
TRANSLATION_DEVICE=cpu
# 或
TRANSLATION_DEVICE=cuda
```

是否能真正启用 GPU，还取决于宿主机驱动、CUDA 运行时以及 Python/PyTorch 版本是否匹配。

## FAQ

### 模型文件不存在怎么办？

确认下面两个路径真实存在：

- `models/lid.176.bin`
- `models/m2m100_418M/`

### 为什么 `/healthz` 也需要认证？

当前实现中，健康检查接口同样受 Basic Auth 保护，用于避免未授权探测。

### 为什么镜像体积比较大？

主要原因不是应用代码，而是：

- 本地翻译模型本身较大
- PyTorch 运行时体积较大

当前 Dockerfile 已经通过多阶段构建尽量压缩非运行时内容。
