import os
import json
import glob

INPUT_DIR = "D:\Projects\Self\pcb_detection\images"       
OUTPUT_DIR = "dataset_lm2596" 
CLASSES = ["components"]      

def convert():
    for split in ['train', 'valid']:
        os.makedirs(f"{OUTPUT_DIR}/{split}/images", exist_ok=True)
        os.makedirs(f"{OUTPUT_DIR}/{split}/labels", exist_ok=True)

    json_files = glob.glob(os.path.join(INPUT_DIR, "*.json"))
    print(f"Tìm thấy {len(json_files)} file JSON...")

    # 80% train, 20% val 
    for idx, json_file in enumerate(json_files):
        subset = "valid" if (idx % 5 == 0) else "train"
        
        with open(json_file, "r", encoding='utf-8') as f:
            data = json.load(f)

        image_width = data["imageWidth"]
        image_height = data["imageHeight"]
        image_name = data["imagePath"].split('\\')[-1].split('/')[-1]
        filename_no_ext = os.path.splitext(image_name)[0]

        src_img_path = os.path.join(INPUT_DIR, image_name)
        dst_img_path = os.path.join(OUTPUT_DIR, subset, "images", image_name)
        
        if os.path.exists(src_img_path):
            import shutil
            shutil.copy(src_img_path, dst_img_path)
        else:
            print(f"Không thấy ảnh: {src_img_path}, bỏ qua.")
            continue

        txt_content = ""
        for shape in data["shapes"]:
            label = shape["label"]
            if label not in CLASSES:
                continue 
            
            class_id = CLASSES.index(label)
            points = shape["points"]

            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            
            x_min = min(x_coords)
            x_max = max(x_coords)
            y_min = min(y_coords)
            y_max = max(y_coords)

            dw = 1. / image_width
            dh = 1. / image_height
            
            w = x_max - x_min
            h = y_max - y_min
            x = (x_min + x_max) / 2.0
            y = (y_min + y_max) / 2.0
            
            x = x * dw
            w = w * dw
            y = y * dh
            h = h * dh
            
            txt_content += f"{class_id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n"

        txt_path = os.path.join(OUTPUT_DIR, subset, "labels", f"{filename_no_ext}.txt")
        with open(txt_path, "w", encoding='utf-8') as f:
            f.write(txt_content)

    print("Chuyển đổi hoàn tất!")
    print(f"Dataset nằm tại thư mục: {OUTPUT_DIR}")

if __name__ == "__main__":
    convert()