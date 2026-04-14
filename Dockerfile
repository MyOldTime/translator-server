# 第一阶段：构建依赖环境，直接使用官方 Python 3.12.13 镜像
FROM python:3.12.13-slim-bookworm AS builder

# 构建阶段的环境变量：
# - 禁止生成 pyc
# - 标准输出无缓冲
# - 强制 UTF-8
# - uv 使用 copy 模式，避免链接问题
# - 项目虚拟环境固定到 /app/.venv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    APP_HOST=0.0.0.0 \
    APP_PORT=8191

WORKDIR /app

# 安装最小系统依赖，并安装 uv
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates libgomp1 \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.local/bin:${PATH}"

# 先复制依赖清单和源码，便于利用 Docker 层缓存
COPY pyproject.toml uv.lock README.md .python-version ./
COPY src ./src
COPY requirements.cpu.txt ./requirements.cpu.txt

# 安装项目基础依赖，并补装 CPU 版 PyTorch
# 最后清理缓存，减少中间层体积
RUN uv sync --python /usr/local/bin/python --frozen --no-dev \
    && uv pip install --python /app/.venv/bin/python -r requirements.cpu.txt \
    && rm -rf /root/.cache /tmp/*

# 第二阶段：运行时镜像，只保留服务运行需要的内容
# 使用 Docker Hub 官方存在的 Python 3.12 slim-bookworm 标签
FROM python:3.12.13-slim-bookworm AS runtime

# 运行时环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8191

WORKDIR /app

# 运行时只安装最小系统依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 拷贝已经准备好的虚拟环境，避免重复安装依赖
COPY --from=builder /app/.venv /app/.venv
# 拷贝应用源码和依赖说明文件
COPY pyproject.toml README.md ./
COPY src ./src
COPY requirements.cpu.txt requirements.cuda.txt ./

# 拷贝本地模型目录，容器启动后直接可用
COPY models ./models

EXPOSE 8191

# 容器启动命令：直接使用虚拟环境中的 Python 启动 uvicorn
CMD ["/app/.venv/bin/python", "-m", "uvicorn", "translator_server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8191"]
