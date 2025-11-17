#!/bin/bash

# Script để khởi động backend server

echo "🚀 Đang khởi động PCB Detection Backend Server..."

# Kiểm tra xem có môi trường ảo không
if [ ! -d "venv" ]; then
    echo "📦 Tạo môi trường ảo Python..."
    python3 -m venv venv
fi

# Kích hoạt môi trường ảo
echo "🔧 Kích hoạt môi trường ảo..."
source venv/bin/activate

# Cài đặt dependencies nếu chưa có
echo "📥 Kiểm tra và cài đặt dependencies..."
pip install -q -r requirements.txt

# Tạo thư mục data nếu chưa có
mkdir -p ../data/artifacts

# Chạy server
echo "✅ Server đang chạy tại http://127.0.0.1:8000"
echo "📚 API Documentation: http://127.0.0.1:8000/docs"
echo ""
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

