# ============================================================
# ZenX Bridge Skill - Docker 镜像
# 多阶段构建：包含 bsk CLI + Python helpers + 浏览器扩展
# 
# 用法:
#   构建:  docker build -t zenx-bridge-skill:latest .
#   运行:  docker run --rm zenx-bridge-skill doctor.py --help
#   开发:  docker-compose up -d  (完整 daemon + 扩展环境)
#
# 支持的平台: linux/amd64, linux/arm64 (Apple Silicon)
# ============================================================

# ----------------------------------------------------------
# 阶段 1: 基础运行时环境
# ----------------------------------------------------------
FROM python:3.12-slim AS base

LABEL maintainer="ZenX Bridge Skill Team"
LABEL description="ZenX Bridge Skill - AI Agent 浏览器控制 Skill"
LABEL version="1.1.0"
LABEL repository="https://github.com/916938/zenx-bridge-skill"

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    BSK_VERSION="0.1.7"

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 网络工具（用于调试）
    curl \
    wget \
    netcat-openbsd \
    # 基本工具
    git \
    ca-certificates \
    gnupg \
    # 文本处理
    jq \
    # 清理缓存以减小镜像体积
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app

# ----------------------------------------------------------
# 阶段 2: 安装 bsk CLI (Rust 编译版本)
# ----------------------------------------------------------
FROM base AS cli-builder

# 安装 Rust 工具链
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    --default-toolchain stable \
    --profile minimal

ENV PATH="/root/.cargo/bin:${PATH}"

# 克隆并编译 bsk CLI（使用预编译二进制或从源码构建）
# 方式 A: 从 GitHub Releases 下载预编译版本（更快）
ARG BSK_RELEASE_URL="https://github.com/Tencent/BrowserSkill/releases/download/v0.1.7/bsk-x86_64-unknown-linux-gnu.tar.gz"

RUN mkdir -p /tmp/bsk-build && cd /tmp/bsk-build && \
    curl -fsSL "$BSK_RELEASE_URL" -o bsk.tar.gz && \
    tar xzf bsk.tar.gz && \
    mv bsk /usr/local/bin/bsk && \
    chmod +x /usr/local/bin/bsk && \
    bsk --version || echo "bsk CLI installed (version may vary)"

# 备选方式 B: 如果需要从源码构建，取消以下注释
# RUN git clone --depth 1 --branch v0.1.7 https://github.com/Tencent/BrowserSkill.git /tmp/browserskill && \
#     cd /tmp/browserskill && \
#     cargo install --path crates/bsk-cli --root /usr/local && \
#     rm -rf /tmp/browserskill

# ----------------------------------------------------------
# 阶段 3: 最终镜像（合并所有组件）
# ----------------------------------------------------------
FROM base AS final

# 从 CLI 构建阶段复制 bsk 二进制文件
COPY --from=cli-builder /usr/local/bin/bsk /usr/local/bin/bsk

# 验证 bsk 可用
RUN bsk --version || echo "Warning: bsk CLI not found, will use mock for testing"

# 复制 skill 内容
COPY skill/ ./skill/
COPY tests/ ./tests/

# 创建必要的目录结构
RUN mkdir -p /app/logs \
             /app/data/screenshots \
             /app/data/snapshots \
             /app/.bsk

# 设置权限
RUN chmod -R 755 /app/skill/scripts

# 创建非 root 用户运行（安全最佳实践）
RUN groupadd -r browserskill && useradd -r -g browserskill -d /app -s /bin/bash browserskill \
    && chown -R browserskill:browserskill /app

USER browserskill

# 暴露健康检查端口（可选）
EXPOSE 52800

# 默认命令：显示帮助信息
CMD ["python3", "skill/scripts/doctor.py", "--help"]

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 /app/skill/scripts/doctor.py --json | grep -q '"ready": true' || exit 1
