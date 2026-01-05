"""auto_relabel.py
Script tự động gán lại class_id cho tất cả file label trong train/labels và valid/labels.
Sử dụng file reference (0006.txt) làm chuẩn để mapping các box theo vị trí.

Cách chạy:
    python auto_relabel.py
"""

from pathlib import Path
import shutil
import math
from datetime import datetime

# Đường dẫn dataset
DATASET_ROOT = r"C:\Users\LENOVO\Downloads\dataset_lm2596-20251229T055104Z-3-001\dataset_lm2596"
REFERENCE_FILE = r"C:\Users\LENOVO\Downloads\dataset_lm2596-20251229T055104Z-3-001\dataset_lm2596\valid\labels\0006.txt"

# 11 linh kiện theo thứ tự đã định nghĩa
CLASS_NAMES = [
    'Tụ hoá vào',           # 0
    'Tụ gốm (dưới)',        # 1
    'Diode Schottky',       # 2
    'IC LM2596',            # 3
    'Tụ gốm cạnh IC',       # 4
    'Trở cạnh IC',          # 5
    'Cuộn cảm',             # 6
    'Biến trở xanh',        # 7
    'Trở cạnh biến trở',    # 8
    'LED',                  # 9
    'Tụ hoá đầu ra'         # 10
]

def read_labels(path):
    """Đọc file label và trả về list (class_id, [x_center, y_center, width, height])"""
    lines = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            parts = s.split()
            cls = int(parts[0])
            coords = list(map(float, parts[1:5]))
            lines.append((cls, coords))
    return lines

def get_centers(labels):
    """Lấy tọa độ tâm từ labels"""
    return [(l[1][0], l[1][1]) for l in labels]

def distance(p1, p2):
    """Tính khoảng cách Euclidean"""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def match_boxes(ref_centers, current_centers):
    """
    Match boxes dựa trên khoảng cách gần nhất (greedy assignment).
    Trả về mapping: current_box_index -> ref_box_index (class_id)
    """
    # Assign boxes following the reference order deterministically.
    # For each reference index (0..), pick the nearest unassigned current box
    # and assign it that class id. Any remaining current boxes are assigned
    # the nearest reference index as fallback.
    n_ref = len(ref_centers)
    n_curr = len(current_centers)

    if n_curr == 0:
        return {}

    mapping = {}
    assigned_currs = set()

    # For each reference in order, choose nearest unassigned current box
    for ref_idx, ref_center in enumerate(ref_centers):
        # stop if all current boxes already assigned
        if len(assigned_currs) >= n_curr:
            break
        # find nearest unassigned current index
        best_j = None
        best_d = None
        for j, curr_center in enumerate(current_centers):
            if j in assigned_currs:
                continue
            d = distance(ref_center, curr_center)
            if best_d is None or d < best_d:
                best_d = d
                best_j = j
        if best_j is not None:
            mapping[best_j] = ref_idx
            assigned_currs.add(best_j)

    # Any remaining unassigned current boxes: assign nearest reference index
    for j in range(n_curr):
        if j in mapping:
            continue
        best_ref = min(range(n_ref), key=lambda i: distance(ref_centers[i], current_centers[j]))
        mapping[j] = best_ref

    return mapping

def update_label_file(label_path, new_class_ids):
    """Cập nhật file label với class_id mới"""
    with open(label_path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    
    output_lines = []
    for i, line in enumerate(lines):
        parts = line.split()
        parts[0] = str(new_class_ids[i])
        output_lines.append(' '.join(parts))
    
    with open(label_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines) + '\n')

def backup_folder(src_folder, backup_root):
    """Backup toàn bộ folder"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_folder = Path(backup_root) / f"backup_{timestamp}"
    
    if Path(src_folder).exists():
        shutil.copytree(src_folder, backup_folder / Path(src_folder).name, 
                       dirs_exist_ok=True)
    return backup_folder

def process_all_labels():
    """Xử lý tất cả file labels trong train và valid"""
    dataset_root = Path(DATASET_ROOT)
    ref_file = Path(REFERENCE_FILE)
    
    if not ref_file.exists():
        print(f"❌ Không tìm thấy file reference: {ref_file}")
        return
    
    # Đọc reference labels
    ref_labels = read_labels(ref_file)
    ref_centers = get_centers(ref_labels)
    
    if len(ref_centers) != 11:
        print(f"⚠️ Cảnh báo: File reference có {len(ref_centers)} boxes, mong đợi 11")
    
    print(f"✅ Đã load reference file với {len(ref_centers)} components")
    print(f"   Reference: {ref_file.name}\n")
    
    # Backup trước khi sửa
    backup_root = dataset_root / "label_backups"
    backup_root.mkdir(exist_ok=True)
    
    print("📦 Đang backup labels...")
    for folder in ['train/labels', 'valid/labels']:
        src = dataset_root / folder
        if src.exists():
            backup_folder(src, backup_root)
            print(f"   ✓ Backed up: {folder}")
    
    # Tìm tất cả file labels
    label_files = []
    for folder in ['train/labels', 'valid/labels']:
        label_dir = dataset_root / folder
        if label_dir.exists():
            label_files.extend(sorted(label_dir.glob('*.txt')))
    
    print(f"\n🔄 Bắt đầu xử lý {len(label_files)} files...\n")
    
    # Xử lý từng file
    updated = 0
    skipped = 0
    
    for label_file in label_files:
        try:
            # Đọc labels hiện tại
            current_labels = read_labels(label_file)
            current_centers = get_centers(current_labels)
            
            if not current_centers:
                print(f"⊘ SKIP: {label_file.name} (empty)")
                skipped += 1
                continue
            # Assign sequential class ids in order of appearance (0,1,2,...)
            if len(current_centers) > len(CLASS_NAMES):
                print(f"⊘ SKIP: {label_file.name} ({len(current_centers)} boxes > {len(CLASS_NAMES)} classes)")
                skipped += 1
                continue
            new_class_ids = list(range(len(current_centers)))
            
            # Cập nhật file
            update_label_file(label_file, new_class_ids)
            
            # Hiển thị thông tin
            class_distribution = {}
            for cid in new_class_ids:
                class_distribution[cid] = class_distribution.get(cid, 0) + 1
            
            dist_str = ', '.join([f"{CLASS_NAMES[cid][:15]}:{cnt}" 
                                 for cid, cnt in sorted(class_distribution.items())])
            
            print(f"✓ {label_file.name}: {len(current_centers)} boxes → [{dist_str}]")
            updated += 1
            
        except Exception as e:
            print(f"✗ ERROR: {label_file.name} - {e}")
            skipped += 1
    
    print(f"\n{'='*70}")
    print(f"🎉 HOÀN THÀNH!")
    print(f"   ✅ Updated: {updated} files")
    print(f"   ⊘ Skipped: {skipped} files")
    print(f"   📦 Backups: {backup_root}")
    print(f"{'='*70}\n")
    
    # Hiển thị danh sách class
    print("📋 Danh sách 11 class đã cập nhật:")
    for i, name in enumerate(CLASS_NAMES):
        print(f"   {i}: {name}")

if __name__ == '__main__':
    process_all_labels()
