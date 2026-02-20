# LiteLLM 测试脚本快速指南

## 环境设置

```bash
# 1. 创建虚拟环境（只需一次）
python3 -m venv .venv

# 2. 安装依赖
source .venv/bin/activate
pip install -r requirements-test.txt
```

## 获取测试 Token

1. 访问 LiteLLM 管理界面：http://localhost:4000/ui/
2. 登录（用户名: admin, 密码: admin123）
3. 在左侧菜单找到 "Keys" → "Create Key"
4. 复制生成的 key（格式: `sk-xxxxxx`）

## 配置测试环境

```bash
# 复制配置模板
cp tests/.env.example tests/.env

# 编辑 tests/.env，填入真实的 key
# LITELLM_MASTER_KEY=sk-你生成的key
```

## 运行测试

```bash
# 激活环境并加载配置
source .venv/bin/activate
source tests/.env

# 快速测试
python3 tests/test_simple.py

# 完整测试套件
python3 tests/test_route.py

# 远程服务器测试
python3 tests/test_remote.py --url http://server:4000 --key sk-xxx
```

## 一键测试脚本

```bash
# 创建快捷脚本
cat > test.sh << 'EOF'
#!/bin/bash
source .venv/bin/activate
source tests/.env
python3 tests/test_route.py
EOF

chmod +x test.sh
./test.sh
```
