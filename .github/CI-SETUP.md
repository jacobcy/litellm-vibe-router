# GitHub Actions CI 配置建议

## 概述

为 LiteLLM Intelligent Router 项目添加 CI/CD 自动化测试和部署流程。

## 建议的 CI 工作流

### 1. 测试工作流 (.github/workflows/test.yml)

```yaml
name: Test

on:
  push:
    branches: [ master, main, develop ]
  pull_request:
    branches: [ master, main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          submodules: recursive
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-test.txt
      
      - name: Start LiteLLM services
        run: |
          # 创建测试用的 .env 文件
          cp .env.example .env
          echo "LITELLM_MASTER_KEY=${{ secrets.LITELLM_MASTER_KEY }}" >> .env
          echo "NEW_API_KEY=${{ secrets.NEW_API_KEY }}" >> .env
          
          # 启动服务
          docker-compose up -d
          
          # 等待服务就绪
          timeout 60 bash -c 'until docker ps | grep healthy; do sleep 2; done'
      
      - name: Run basic health check
        run: |
          python3 tests/test_all_6_models.py
        env:
          LITELLM_MASTER_KEY: ${{ secrets.LITELLM_MASTER_KEY }}
          LITELLM_BASE_URL: http://localhost:4000
      
      - name: Run full test suite (允许部分失败)
        continue-on-error: true
        run: |
          python3 tests/test_route.py
        env:
          LITELLM_MASTER_KEY: ${{ secrets.LITELLM_MASTER_KEY }}
          LITELLM_BASE_URL: http://localhost:4000
      
      - name: Show container logs on failure
        if: failure()
        run: |
          docker-compose logs litellm
          docker-compose logs cliproxyapi
      
      - name: Cleanup
        if: always()
        run: docker-compose down -v

  lint:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install linters
        run: |
          pip install flake8 black isort
      
      - name: Run flake8
        run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
      
      - name: Check code formatting
        run: black --check .
      
      - name: Check import order
        run: isort --check-only .
```

### 2. Docker Build 工作流 (.github/workflows/docker.yml)

```yaml
name: Docker Build

on:
  push:
    branches: [ master, main ]
    tags: [ 'v*' ]
  pull_request:
    branches: [ master, main ]

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          submodules: recursive
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GitHub Container Registry
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 3. 部署工作流 (.github/workflows/deploy.yml)

```yaml
name: Deploy

on:
  push:
    tags: [ 'v*' ]
  workflow_dispatch:

jobs:
  deploy-prod:
    runs-on: ubuntu-latest
    environment: production
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Deploy to production server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /path/to/litellm
            git pull origin master
            ./deploy.sh
            docker-compose ps
```

## 需要配置的 Secrets

在 GitHub repository settings → Secrets and variables → Actions 中添加：

1. **LITELLM_MASTER_KEY**: LiteLLM master key (for testing)
2. **NEW_API_KEY**: New API key
3. **CHAT_AUTO_API_KEY**: CLIProxyAPI key (optional for CI)
4. **ARK_API_KEY**: Ark API key (optional for CI)
5. **PROD_HOST**: 生产服务器地址 (for deployment)
6. **PROD_USER**: SSH 用户名
7. **PROD_SSH_KEY**: SSH 私钥

## CI 策略

### 测试范围

1. **基础测试** (必须通过):
   - Health check
   - 4个基础模型 (auto-chat, auto-chat-mini, auto-claude, auto-claude-mini)
   
2. **可选测试** (允许失败):
   - auto-codex, auto-codex-mini (依赖外部 quota)
   - 完整的路由测试

### 触发条件

- **Pull Request**: 运行所有测试
- **Push to master**: 测试 + Docker build
- **Tag push (v*)**: 测试 + Build + Deploy

### 性能优化

1. **缓存策略**:
   - Docker layer caching
   - Python依赖缓存
   
2. **并行测试**:
   - Matrix strategy (多Python版本)
   - 并行运行lint和test

3. **快速失败**:
   - Health check失败立即停止
   - 关键测试失败不运行后续步骤

## 本地测试命令

在提交前本地验证CI流程：

```bash
# 模拟CI环境测试
docker-compose up -d && sleep 10
python3 tests/test_all_6_models.py
docker-compose down -v

# Lint检查
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
black --check .
isort --check-only .
```

## 实施步骤

1. ✅ 创建测试脚本 (已完成)
2. ⬜ 创建 `.github/workflows/` 目录
3. ⬜ 添加上述3个工作流文件
4. ⬜ 配置 GitHub Secrets
5. ⬜ 创建首个PR测试CI
6. ⬜ 优化和调整工作流

## 注意事项

1. **API Quota**: auto-codex 测试可能因 quota 失败，应设置 `continue-on-error: true`
2. **Secrets 安全**: 不要在日志中打印敏感信息
3. **CLIProxyAPI**: 子模块需要 `submodules: recursive`
4. **超时设置**: 某些模型响应慢，需要合理的超时时间
5. **清理**: 每次测试后清理 Docker 资源避免占用

## 推荐的 Badge

在 README.md 中添加：

```markdown
[![Test](https://github.com/jacobcy/litellm-vibe-router/workflows/Test/badge.svg)](https://github.com/jacobcy/litellm-vibe-router/actions/workflows/test.yml)
[![Docker Build](https://github.com/jacobcy/litellm-vibe-router/workflows/Docker%20Build/badge.svg)](https://github.com/jacobcy/litellm-vibe-router/actions/workflows/docker.yml)
```
