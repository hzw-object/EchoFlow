#!/bin/bash

# EchoFlow 启动脚本

echo "🚀 启动 EchoFlow 实时语音合成系统..."

# 检查 Python 环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python 3"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
if [ ! -f "backend/.env" ]; then
    echo "⚠️  警告: 未找到 backend/.env 文件"
    echo "📝 请复制 backend/.env.example 为 backend/.env 并配置"
fi

# 安装依赖（如果需要）
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python3 -m venv venv
fi

echo "📦 激活虚拟环境并安装依赖..."
source venv/bin/activate
pip install -q -r requirements.txt

# 启动后端服务
echo "🎙️  启动后端服务..."
cd backend
python server.py &
BACKEND_PID=$!

cd ..

# 启动前端服务
echo "🌐 启动前端服务..."
cd frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!

cd ..

echo ""
echo "✅ EchoFlow 已启动！"
echo "📡 后端服务: http://localhost:8000"
echo "🌐 前端界面: http://localhost:8080"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户中断
trap "echo ''; echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT

wait

