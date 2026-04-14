# translator-server

基于 `fastText` 语种识别模型 `lid.176.bin` 和本地 `M2M100` 模型 `m2m100_418M` 构建的 FastAPI 翻译服务，提供统一的 HTTP 接口用于文本翻译。

## 功能概览

- 自动识别源语言，也支持手动指定源语言
- 使用本地模型目录运行，不依赖在线拉取模型
- 基于 `uv` 管理依赖与运行环境
- 提供健康检查接口和单一翻译接口
- 内置 Basic Auth 认证
- 支持 Docker 镜像构建与离线部署

## 技术栈

- Python `3.12.13`
- FastAPI
- fastText
- Transformers
- PyTorch (CPU 默认，CUDA 可选)
- uv

## 目录结构

```text
.
├─ models/
│  ├─ lid.176.bin
│  └─ m2m100_418M/
├─ src/translator_server/
│  ├─ app.py
│  ├─ config.py
│  ├─ main.py
│  ├─ schemas.py
│  ├─ security.py
│  └─ services/
├─ Dockerfile
├─ docker-compose.yml
├─ pyproject.toml
└─ README.md
```

## 环境要求

- Python `3.12.13`
- 已安装 `uv`
- 已安装 `Git` 和 `Git LFS`
- 本地已准备模型文件：
  - `models/lid.176.bin`
  - `models/m2m100_418M/`

## 获取项目

首次克隆时请一并拉取子模块：

```bash
git clone --recurse-submodules <your-repo-url>
```

如果仓库已存在，可补拉子模块：

```bash
git submodule update --init --recursive
```

如果尚未初始化 Git LFS，请先执行：

```bash
git lfs install
```

单独更新翻译模型子模块时可执行：

```bash
git submodule update --remote models/m2m100_418M
```

## 本地开发

安装依赖：

```bash
uv python pin 3.12.13
uv sync
uv pip install -r requirements.cpu.txt
```

启动服务：

```bash
uv run translator-server
```

也可以直接使用 `uvicorn` 启动：

```bash
uv run uvicorn translator_server.app:create_app --factory --host 0.0.0.0 --port 8191
```

Windows 环境可直接运行：

```bat
run_service.bat
```

服务默认监听 `8191` 端口。

## 配置说明

服务支持通过环境变量覆盖默认配置：

| 变量名 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_NAME` | `translator-server` | 应用名称 |
| `APP_ENV` | `dev` | 运行环境标识 |
| `APP_HOST` | `0.0.0.0` | 监听地址 |
| `APP_PORT` | `8191` | 监听端口 |
| `LID_MODEL_PATH` | `models/lid.176.bin` | fastText 语种识别模型路径 |
| `TRANSLATION_MODEL_PATH` | `models/m2m100_418M` | 翻译模型目录 |
| `DEFAULT_TARGET_LANG` | `zh` | 默认目标语言 |
| `MAX_BATCH_SIZE` | `8` | 批处理大小 |
| `MAX_INPUT_CHARS` | `20000` | 单次请求最大字符数 |
| `SEGMENT_MAX_CHARS` | `400` | 分段翻译时每段最大字符数 |
| `MAX_LENGTH` | `512` | 生成最大长度 |
| `MAX_NEW_TOKENS` | `512` | 最大新增 token 数 |
| `TRANSLATION_DEVICE` | `cpu` | 推理设备，如 `cpu` 或 `cuda` |
| `NUM_BEAMS` | `1` | Beam search 参数 |
| `BASIC_AUTH_USERNAME` | `admin` | Basic Auth 用户名 |
| `BASIC_AUTH_PASSWORD` | `Admin@123` | Basic Auth 密码 |

> 生产环境请务必覆盖默认账号密码。

## Docker 部署

推荐在 Linux 环境中使用 Docker 部署。镜像构建时会：

- builder/runtime 都基于官方 `python:3.12.13-slim-bookworm`
- 在 builder 阶段安装 `uv`
- 通过 `uv sync --python /usr/local/bin/python --frozen --no-dev` 安装基础依赖，并额外安装 CPU 版 PyTorch
- 将本地 `models/` 目录复制到镜像中

构建镜像：

```bash
docker build -t translator-server:latest .
```

运行容器：

```bash
docker run -d \
  --name translator-server \
  --restart always \
  -p 8191:8191 \
  translator-server:latest
```

使用 Compose：

```bash
docker compose up -d --build
```

`docker-compose.yml` 默认配置了 `restart: always`，适合在宿主机或 Docker 服务重启后自动拉起服务。

离线部署时可先导出镜像：

```bash
docker save -o translator-server.tar translator-server:latest
```

在目标机器导入镜像：

```bash
docker load -i translator-server.tar
```

## API 说明

所有接口均启用 Basic Auth。

- 默认用户名：`admin`
- 默认密码：`Admin@123`

### 健康检查

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

### 文本翻译

```http
POST /api/v1/translate
Content-Type: application/json
Authorization: Basic <base64(username:password)>
```

请求示例：

```json
{
  "text": "Hello world",
  "target_lang": "zh"
}
```

如果需要手动指定源语言：

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

## 常见问题

### 1. 启动时报模型不存在

请确认以下路径存在且内容完整：

- `models/lid.176.bin`
- `models/m2m100_418M/`

### 2. Docker 镜像体积较大

这是因为镜像中包含本地翻译模型和 PyTorch 运行时。当前 Dockerfile 已做了这些优化：

- 使用多阶段构建
- 移除构建缓存
- 排除 `models/` 目录中 Python 推理不需要的 `*.ot`、`*.md`、`*.zip`

如果镜像仍然偏大，通常最大的来源仍然是模型文件本身。

### 3. 默认为什么不用 CUDA

当前项目默认固定使用 `cpu`，不会因为机器上存在 CUDA 就自动切换到 GPU。

默认 CPU 依赖安装方式：

```bash
uv pip install -r requirements.cpu.txt
```

如果你需要启用 CUDA：

1. 将环境变量 `TRANSLATION_DEVICE` 设置为 `cuda`
2. 额外按需安装 CUDA 版本的 PyTorch 依赖，可参考根目录的 `requirements.cuda.txt`

例如：

```bash
uv pip install -r requirements.cuda.txt
```

是否能真正启用，还取决于宿主机驱动、CUDA 运行时和容器/系统环境是否匹配。

### 4. 健康检查为什么也需要认证

当前实现中，`/healthz` 同样启用了 Basic Auth，用于避免未授权探测。
