"""convert.py
Rewrite YOLO label files so class_id simply follows the box order (0, 1, 2, ...).

Usage example:
  python convert.py --dataset-root "C:\path\to\dataset" --backup backups

Each label file is rewritten with class ids assigned in order of appearance,
starting from 0. By default the script allows up to 11 classes (0..10) and
skips files that contain more boxes than this limit.
"""

from pathlib import Path
import argparse
import shutil
import sys

MAX_CLASSES = 11  # default limit -> class ids 0..10


def read_labels(path):
    lines = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            parts = s.split()
            nums = list(map(float, parts[1:5]))
            lines.append((int(parts[0]), nums))
    return lines


def find_label_files(root):
    root = Path(root)
    files = []
    for folder in ('train/labels', 'valid/labels', 'val/labels'):
        p = root / folder
        if p.exists():
            files.extend(sorted(p.glob('*.txt')))
    # also check root-level labels
    root_labels = root / 'labels'
    if root_labels.exists():
        files.extend(sorted(root_labels.glob('*.txt')))
    return [str(p) for p in files]


def backup_labels(all_label_files, backup_dir):
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    for f in all_label_files:
        src = Path(f)
        dst = backup_dir / src.name
        if not dst.exists():
            shutil.copy(src, dst)


def rewrite_labels_file(label_path, new_classes):
    with open(label_path, 'r', encoding='utf-8') as f:
        lines = [l.strip() for l in f.readlines() if l.strip()]
    out_lines = []
    for i, line in enumerate(lines):
        parts = line.split()
        parts[0] = str(int(new_classes[i]))
        out_lines.append(' '.join(parts))
    with open(label_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines) + ('\n' if out_lines else ''))


def sequential_classes(count, max_classes):
    if count > max_classes:
        raise ValueError(f"{count} boxes exceeds max_classes={max_classes}")
    return list(range(count))


def main():
    parser = argparse.ArgumentParser(description='Rewrite YOLO labels with sequential class ids (0..10 by default).')
    parser.add_argument('--dataset-root', required=True, help='Dataset root containing train/ and valid/ folders')
    parser.add_argument('--backup', default='label_backups', help='Folder to copy original label files into (inside dataset-root)')
    parser.add_argument('--max-classes', type=int, default=MAX_CLASSES, help='Maximum number of sequential classes allowed (default 11 => ids 0..10)')
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root)
    label_files = find_label_files(dataset_root)
    if not label_files:
        print('No label files found under', dataset_root)
        sys.exit(1)

    backup_folder = dataset_root / args.backup
    print('Backing up label files to', str(backup_folder))
    backup_labels(label_files, backup_folder)

    updated = 0
    skipped = 0
    for lf in label_files:
        lines = read_labels(lf)
        if not lines:
            skipped += 1
            continue
        try:
            new_classes = sequential_classes(len(lines), args.max_classes)
        except ValueError as e:
            print('Skip', lf, '-', e)
            skipped += 1
            continue
        rewrite_labels_file(lf, new_classes)
        updated += 1

    print(f'Done. Updated: {updated}, Skipped: {skipped}. Originals in {backup_folder}')


if __name__ == '__main__':
    main()
