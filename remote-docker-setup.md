# 远程 Docker 管理配置 - MacBook 本地配置

## 架构说明

```
┌─────────────────┐                   ┌─────────────────┐
│  MacBook (本地)  │                   │  mac mini (远程)  │
│  Docker 客户端   │◄──────────────────►│  Docker 服务器    │
│  工作环境         │  SSH 连接          │  Docker daemon   │
└─────────────────┘                   └─────────────────┘
        │                                      │
        │                                      ▼
        │                             ┌─────────────────┐
        │                             │  frpc → bghunt.cn:7085
        │                             └─────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│  连接方式:                                       │
│  1. Tailscale: 100.112.203.89 (直连)            │
│  2. Frps:      bghunt.cn:7085 (通过 frps 转发)  │
└─────────────────────────────────────────────────┘
```

---

## 步骤 0：远程服务器配置（mac mini）

**在 mac mini 上执行一次**，确保 SSH 非交互式登录能找到 docker 命令：

```bash
# 配置非交互式 shell 的 PATH
echo 'export PATH="/usr/local/bin:$PATH"' >> ~/.zshenv

# 验证非交互式 SSH 能找到 docker
ssh chenyi@localhost "which docker"
# 应该输出: /usr/local/bin/docker

ssh chenyi@localhost "docker --version"
# 应该输出: Docker version 28.4.0, build xxxxxxx
```

---

## 步骤 1：安装 Docker CLI（仅命令行，MacBook 本地）

在 MacBook 上执行：

```bash
# 下载 Docker CLI（约 50MB，不含 daemon）
curl -fsSL https://download.docker.com/mac/static/stable/aarch64/docker-28.4.0.tgz -o docker.tgz
tar xzvf docker.tgz
sudo cp docker/docker /usr/local/bin/
rm -rf docker docker.tgz

# 验证安装
docker --version
# 输出: Docker version 28.4.0, build xxxxxxx
```

---

## 步骤 2：配置 SSH Key 认证（免密码）

### Tailscale 方式

```bash
# 生成 SSH key（如果没有）
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "macbook"

# 复制 key 到 mac mini
ssh-copy-id chenyi@100.112.203.89

# 测试连接
ssh chenyi@100.112.203.89 "docker ps"
```

### Frps 方式

```bash
# 复制 key 到 frps 转发端口
ssh-copy-id -p 7085 chenyi@bghunt.cn

# 测试连接
ssh -p 7085 chenyi@bghunt.cn "docker ps"
```

---

## 步骤 3：配置 Docker Context

### 方式一：Tailscale（推荐，直连最快）

```bash
# 创建 context
docker context create macmini-tailscale \
  --docker "host=ssh://chenyi@100.112.203.89"

# 切换到远程
docker context use macmini-tailscale

# 验证
docker ps
```

### 方式二：Frps（通过 bghunt.cn 转发）

```bash
# 创建 context
docker context create macmini-frps \
  --docker "host=ssh://chenyi@bghunt.cn:7085"

# 切换到远程
docker context use macmini-frps

# 验证
docker ps
```

---

## 日常使用命令

### Context 管理

```bash
# 查看所有 context
docker context ls

# 切换到 Tailscale 方式
docker context use macmini-tailscale

# 切换到 Frps 方式
docker context use macmini-frps

# 切换回本地（如果本地有 Docker）
docker context use default
```

### LiteLLM 管理

```bash
# 查看容器状态
docker ps

# 查看日志
docker logs litellm-vibe-router

# 实时日志
docker logs -f litellm-vibe-router

# 只看路由决策
docker logs litellm-vibe-router 2>&1 | grep VIBE-ROUTER

# 重启服务
docker restart litellm-vibe-router

# 重启所有服务
docker-compose -f ~/liteLLM/docker-compose.yml restart

# 停止所有服务
docker-compose -f ~/liteLLM/docker-compose.yml down

# 启动所有服务
docker-compose -f ~/liteLLM/docker-compose.yml up -d

# 查看资源使用
docker stats
```

---

## 故障排查

### SSH 连接测试

```bash
# Tailscale
ssh -v chenyi@100.112.203.89

# Frps
ssh -v -p 7085 chenyi@bghunt.cn
```

### Docker Context 问题

```bash
# 查看当前 context
docker context ls

# 查看 context 详情
docker context inspect macmini-tailscale
docker context inspect macmini-frps

# 重新创建（如果损坏）
docker context rm macmini-tailscale
docker context create macmini-tailscale \
  --docker "host=ssh://chenyi@100.112.203.89"
```

### Tailscale 网络问题

```bash
# 检查状态
tailscale status

# 测试连通性
ping 100.112.203.89

# 重新连接
tailscale up
```

---

## 两种方式对比

| 特性 | Tailscale | Frps |
|------|-----------|------|
| 命令 | `ssh://chenyi@100.112.203.89` | `ssh://chenyi@bghunt.cn:7085` |
| 延迟 | 最低（直连） | 稍高（转发） |
| 依赖 | Tailscale 网络 | frps 服务器 |
| 推荐度 | ⭐⭐⭐ | ⭐⭐ |

**建议**：优先使用 Tailscale，Frps 作为备用。

---

## 快速配置脚本

将以下内容保存为 `setup-docker-remote.sh`：

```bash
#!/bin/bash

echo "=== 安装 Docker CLI ==="
curl -fsSL https://download.docker.com/mac/static/stable/aarch64/docker-28.4.0.tgz -o docker.tgz
tar xzvf docker.tgz
sudo cp docker/docker /usr/local/bin/
rm -rf docker docker.tgz
docker --version

echo ""
echo "=== 配置 SSH Key ==="
if [ ! -f ~/.ssh/id_ed25519 ]; then
  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -C "macbook"
fi

echo ""
echo "=== 请选择连接方式 ==="
echo "1) Tailscale (推荐)"
echo "2) Frps"
read -p "请输入选择 (1 或 2): " choice

if [ "$choice" = "1" ]; then
  echo "配置 Tailscale 方式..."
  ssh-copy-id chenyi@100.112.203.89
  docker context create macmini-tailscale \
    --docker "host=ssh://chenyi@100.112.203.89"
  docker context use macmini-tailscale
  echo "✓ 已切换到 macmini-tailscale"
else
  echo "配置 Frps 方式..."
  ssh-copy-id -p 7085 chenyi@bghunt.cn
  docker context create macmini-frps \
    --docker "host=ssh://chenyi@bghunt.cn:7085"
  docker context use macmini-frps
  echo "✓ 已切换到 macmini-frps"
fi

echo ""
echo "=== 测试连接 ==="
docker ps
echo ""
echo "✓ 配置完成！"
```

运行：

```bash
chmod +x setup-docker-remote.sh
./setup-docker-remote.sh
```
