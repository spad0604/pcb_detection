#!/bin/bash

# Script để khởi động Flutter app

echo "🚀 Đang khởi động PCB Detection Flutter App..."

# Kiểm tra Flutter đã cài đặt chưa
if ! command -v flutter &> /dev/null; then
    echo "❌ Flutter chưa được cài đặt hoặc không có trong PATH"
    echo "Vui lòng cài đặt Flutter SDK và thêm vào PATH"
    exit 1
fi

# Lấy dependencies
echo "📥 Đang tải dependencies..."
flutter pub get

# Kiểm tra platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
else
    PLATFORM="linux"
fi

echo "🖥️  Đang chạy ứng dụng trên $PLATFORM..."
echo "⚠️  Lưu ý: Đảm bảo backend server đã chạy tại http://127.0.0.1:8000"
echo ""

flutter run -d $PLATFORM

