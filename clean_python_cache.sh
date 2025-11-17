#!/bin/bash

# Script để xóa tất cả cache Python

echo "🧹 Đang xóa Python cache..."

# 1. Xóa __pycache__ và .pyc trong source code (không xóa trong venv)
echo "📁 Xóa __pycache__ và .pyc files trong source code..."
find . -type d -name "__pycache__" -not -path "*/venv/*" -not -path "*/.venv/*" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -not -path "*/venv/*" -not -path "*/.venv/*" -delete 2>/dev/null
find . -type f -name "*.pyo" -not -path "*/venv/*" -not -path "*/.venv/*" -delete 2>/dev/null
find . -type f -name "*.pyd" -not -path "*/venv/*" -not -path "*/.venv/*" -delete 2>/dev/null

# 2. Xóa .pyc trong thư mục hiện tại
echo "🗑️  Xóa .pyc files..."
find . -name "*.pyc" -delete 2>/dev/null

# 3. Xóa pip cache (tùy chọn - có thể tiết kiệm nhiều dung lượng)
read -p "❓ Xóa pip cache? (~11GB) (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📦 Xóa pip cache..."
    pip cache purge 2>/dev/null || python3 -m pip cache purge 2>/dev/null
    echo "✅ Đã xóa pip cache"
else
    echo "⏭️  Bỏ qua pip cache"
fi

# 4. Xóa Python bytecode cache
echo "🧼 Xóa Python bytecode cache..."
python3 -Bc "import compileall; compileall.compile_dir('.', force=True, quiet=1)" 2>/dev/null || true

# 5. Xóa pytest cache nếu có
echo "🧪 Xóa pytest cache..."
find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null

# 6. Xóa mypy cache nếu có
echo "📝 Xóa mypy cache..."
find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null

# 7. Xóa coverage cache nếu có
echo "📊 Xóa coverage cache..."
find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null
find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null

echo ""
echo "✅ Hoàn tất! Đã xóa Python cache."
echo ""
echo "💡 Lưu ý:"
echo "   - Cache trong venv không bị xóa (sẽ tự tạo lại khi cần)"
echo "   - Nếu muốn xóa cache trong venv, có thể xóa thư mục venv và tạo lại"

