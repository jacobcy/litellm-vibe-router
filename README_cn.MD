# LiteLLM 智能路由（中文速读版）

## 1) 项目做什么
- 通过虚拟模型（如 `auto-chat`、`auto-codex`、`auto-claude`）统一入口。
- LiteLLM 负责鉴权与路由，后端按层级自动 fallback。
- 当前一键编排已包含：`litellm`、`new-api`、`cliproxyapi`、`postgres`、`redis`。

## 2) 一键脚本（最常用）
```bash
# 默认：全量启动
./deploy.sh
./deploy.sh up

# 全量升级：拉最新镜像并重建
./deploy.sh update

# 只启动部分服务（逗号分隔）
./deploy.sh up --services litellm,new-api
./deploy.sh up --services redis,postgres

# 只升级部分服务
./deploy.sh update --services litellm

# 查看帮助
./deploy.sh --help
```

可选服务名：
- `litellm`
- `new-api`
- `cliproxyapi`
- `postgres`
- `redis`

## 3) 快速开始
```bash
chmod +x deploy.sh QUICKSTART.sh
git submodule update --init --recursive
./deploy.sh up
```

启动后默认端口：
- LiteLLM: `http://localhost:4000`
- New API: `http://localhost:3000`
- CLIProxyAPI: `http://localhost:8317`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`

## 4) 常用验证命令
```bash
# 健康检查（LiteLLM）
curl -s http://localhost:4000/health/liveliness

# 模型列表（需要主 key）
curl -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  http://localhost:4000/v1/models

# 发送测试请求
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"auto-chat","messages":[{"role":"user","content":"hi"}]}'
```

## 5) 数据目录与迁移说明
- `new-api` 数据已固定在当前仓库：`./new-api/data`。
- 如果你之前用的是旧路径（例如 `/Users/chenyi/new-api/data`），现在以仓库内路径为准。

## 6) 常见问题
- `./deploy.sh -h` 以前不可用：现在请用 `./deploy.sh --help`（`-h` 也支持）。
- 只启 `litellm` 时依赖会自动拉起（compose `depends_on`）。
- 如果迁移到 Colima 后挂载异常，确认 Colima 已挂载项目路径（如 `/Volumes/Cube`）。

## 7) 你最可能用到的三条命令
```bash
./deploy.sh up
./deploy.sh update
./deploy.sh up --services litellm,new-api
```
