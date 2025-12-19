from ultralytics import YOLO

def train_model():
    model = YOLO('yolov8n.pt') 


    results = model.train(
        data='./pcb_detection/yolo/dataset_lm2596/data.yaml',
        epochs=100,
        imgsz=640,
        patience=20,
        batch=16,
        project='runs/detect',
        name='lm2596_training',


        degrees=15.0,
        translate=0.1,
        scale=0.5,
        flipud=0.5,
        fliplr=0.5,

        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,

        mosaic=1.0,
        mixup=0.0,
        copy_paste=0.0,
        )

    print("Training hoàn tất. File model nằm tại: /pcb_detection/yolo/runs/detect/lm2596_training/weights/best.pt")

if __name__ == '__main__':
    train_model()