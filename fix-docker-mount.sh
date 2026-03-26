#!/bin/bash
set -e

echo "=== Docker Desktop 文件挂载问题修复脚本 ==="
echo ""
echo "问题：Docker Desktop for Mac 将文件挂载变成了空目录"
echo ""
echo "解决方案选项："
echo "1. 重启 Docker Desktop（推荐，最快）"
echo "2. 将配置嵌入镜像（已完成 CLI Proxy API）"
echo "3. 使用环境变量或 Docker Config"
echo ""
read -p "是否重启 Docker Desktop? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "正在重启 Docker Desktop..."
    osascript -e 'quit app "Docker"'
    sleep 5
    open -a Docker
    echo "等待 Docker Desktop 启动..."
    sleep 30
    echo "Docker Desktop 已重启，现在重新部署服务..."
    docker-compose down && docker-compose up -d
    echo "✅ 修复完成！"
fi
