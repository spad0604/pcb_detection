#!/bin/bash

# Script để xóa tất cả data đã train - reset về trạng thái ban đầu

echo "🗑️  Đang xóa tất cả data đã train..."

# Xác định thư mục data (có thể ở 2 vị trí)
DATA_DIR1="../data"  # Embedded/data
DATA_DIR2="./data"   # Embedded/backend/data

# Function để xóa data từ một thư mục
clean_data_dir() {
    local DATA_DIR=$1
    local ARTIFACTS_DIR="$DATA_DIR/artifacts"
    local DATASET_DIR="$DATA_DIR/dataset"
    local DATASET_JSON="$DATA_DIR/dataset.json"
    
    if [ ! -d "$DATA_DIR" ]; then
        return 0  # Skip nếu thư mục không tồn tại
    fi
    
    # 1. Xóa model đã train
    if [ -d "$ARTIFACTS_DIR" ]; then
        rm -rf "$ARTIFACTS_DIR"/*
        rm -rf "$ARTIFACTS_DIR"/.* 2>/dev/null  # Xóa hidden files
        echo "   ✅ Đã xóa tất cả files trong $ARTIFACTS_DIR"
    fi
    
    # 2. Xóa dataset (ảnh đã upload)
    if [ -d "$DATASET_DIR" ]; then
        rm -rf "$DATASET_DIR"/*
        echo "   ✅ Đã xóa tất cả ảnh trong $DATASET_DIR"
    fi
    
    # 3. Xóa metadata dataset
    if [ -f "$DATASET_JSON" ]; then
        rm -f "$DATASET_JSON"
        echo "   ✅ Đã xóa $DATASET_JSON"
    fi
    
    # Tạo lại cấu trúc thư mục và file rỗng
    mkdir -p "$ARTIFACTS_DIR"
    mkdir -p "$DATASET_DIR"
    echo "[]" > "$DATASET_JSON"
    echo "   ✅ Đã tạo lại cấu trúc thư mục và dataset.json (rỗng)"
}

# Xóa data từ cả 2 vị trí có thể
echo "📂 Kiểm tra và xóa data ở Embedded/data..."
clean_data_dir "$DATA_DIR1"

echo "📂 Kiểm tra và xóa data ở Embedded/backend/data..."
clean_data_dir "$DATA_DIR2"

echo ""
echo "✅ Hoàn tất! Đã reset tất cả data."
echo ""
echo "📋 Tóm tắt:"
echo "   - Model đã train (artifacts/): Đã xóa"
echo "   - Dataset (ảnh trong dataset/): Đã xóa"
echo "   - Metadata dataset (dataset.json): Đã reset"
echo ""
echo "💡 Bây giờ bạn có thể:"
echo "   1. Upload ảnh mới vào dataset"
echo "   2. Train model mới"
echo "   3. Test inference"

