# translator-server

一个基于 FastAPI 的本地翻译服务，使用 `fastText` 进行语种识别，使用本地 `M2M100` 模型完成文本翻译。

适合下面这类场景：

- 需要统一的 HTTP 翻译接口
- 希望完全使用本地模型，不依赖在线推理
- 需要在内网、离线环境或受控环境中部署

## Highlights

- Auto-detect 源语言，也支持手动指定 `source_lang`
- 本地模型推理，无需运行时下载模型
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

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `translator-server` | 应用名称 |
| `APP_ENV` | `dev` | 运行环境 |
| `APP_HOST` | `0.0.0.0` | 监听地址 |
| `APP_PORT` | `8191` | 监听端口 |
| `LID_MODEL_PATH` | `models/lid.176.bin` | fastText 语种识别模型路径 |
| `TRANSLATION_MODEL_PATH` | `models/m2m100_418M` | 翻译模型目录 |
| `DEFAULT_TARGET_LANG` | `zh` | 默认目标语言 |
| `MAX_BATCH_SIZE` | `8` | 批处理大小 |
| `MAX_INPUT_CHARS` | `20000` | 单次请求最大字符数 |
| `SEGMENT_MAX_CHARS` | `400` | 单段最大字符数 |
| `MAX_LENGTH` | `512` | 生成最大长度 |
| `MAX_NEW_TOKENS` | `512` | 最大新增 token 数 |
| `TRANSLATION_DEVICE` | `cpu` | 推理设备，通常为 `cpu` 或 `cuda` |
| `NUM_BEAMS` | `1` | Beam search 参数 |
| `BASIC_AUTH_USERNAME` | `admin` | Basic Auth 用户名 |
| `BASIC_AUTH_PASSWORD` | `Admin@123` | Basic Auth 密码 |

生产环境建议至少覆盖以下变量：

```bash
APP_ENV=prod
BASIC_AUTH_USERNAME=your-user
BASIC_AUTH_PASSWORD=your-password
```

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

项目默认安装 CPU 依赖：

```bash
uv pip install -r requirements.cpu.txt
```

如果需要启用 CUDA：

1. 安装 CUDA 对应版本的 PyTorch 依赖
2. 将 `TRANSLATION_DEVICE` 设置为 `cuda`

示例：

```bash
uv pip install -r requirements.cuda.txt
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
