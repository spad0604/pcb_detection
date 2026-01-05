from pathlib import Path
import math

def read_centers(p):
    centers=[]
    with open(p,'r',encoding='utf-8') as f:
        for line in f:
            s=line.strip()
            if not s: continue
            parts=s.split()
            x=float(parts[1]); y=float(parts[2])
            centers.append((x,y))
    return centers

def dist(a,b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

# paths
root=Path(r"C:\Users\LENOVO\Downloads\dataset_lm2596-20251229T055104Z-3-001\dataset_lm2596")
ref=root / 'valid' / 'labels' / '0006.txt'
cur=root / 'valid' / 'labels' / '0026.txt'

ref_centers=read_centers(ref)
cur_centers=read_centers(cur)

print('Reference centers (index -> (x,y))')
for i,c in enumerate(ref_centers):
    print(i, c)
print('\nCurrent centers (index -> (x,y))')
for j,c in enumerate(cur_centers):
    print(j, c)

# build distance list
pairs=[]
for i,rc in enumerate(ref_centers):
    for j,cc in enumerate(cur_centers):
        pairs.append((dist(rc,cc), i, j))
pairs.sort()

# greedy assign
assigned_refs=set(); assigned_cur=set(); mapping={}
for d,i,j in pairs:
    if i in assigned_refs or j in assigned_cur: continue
    mapping[j]=i
    assigned_refs.add(i); assigned_cur.add(j)

# assign remaining cur (if any) to nearest ref
for j in range(len(cur_centers)):
    if j in mapping: continue
    best=min(range(len(ref_centers)), key=lambda i: dist(ref_centers[i], cur_centers[j]))
    mapping[j]=best

print('\nAssignments (cur_index -> ref_index):')
for j in sorted(mapping.keys()):
    i=mapping[j]
    print(f'{j} -> {i}   dist={dist(ref_centers[i], cur_centers[j]):.6f}')

# show final classes order as in file (class ids at file lines)
print('\nFinal class ids in file order:')
ordered=[mapping[j] for j in range(len(cur_centers))]
print(ordered)
