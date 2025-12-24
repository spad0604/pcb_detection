#!/usr/bin/env python3
"""Capture snapshots from each camera to identify which is which."""

import cv2
import os
import subprocess
import time

def capture_snapshot(index, output_path):
    """Capture a snapshot from camera at given index."""
    print(f"\n{'='*60}")
    print(f"Capturing from Camera {index}...")
    print(f"{'='*60}")
    
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print(f"❌ Cannot open camera {index}")
        return False
    
    # Wait a bit for camera to warm up
    time.sleep(1)
    
    # Read a few frames to let camera adjust
    for _ in range(5):
        cap.read()
    
    ret, frame = cap.read()
    if not ret or frame is None:
        print(f"❌ Camera {index} opened but cannot read frame")
        cap.release()
        return False
    
    # Add text overlay
    height, width = frame.shape[:2]
    text = f"Camera Index: {index}"
    font_scale = width / 640.0  # Scale text based on resolution
    cv2.putText(frame, text, (10, int(30 * font_scale)), 
               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), 2, cv2.LINE_AA)
    
    # Save snapshot
    cv2.imwrite(output_path, frame)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"✅ Snapshot saved: {output_path}")
    print(f"   Resolution: {width}x{height}")
    
    cap.release()
    return True

def open_image(path):
    """Open image with default Windows viewer."""
    try:
        os.startfile(path)
        return True
    except Exception as e:
        print(f"⚠️  Could not auto-open image: {e}")
        return False

def main():
    print("="*60)
    print("Camera Snapshot Tool")
    print("="*60)
    print("\nThis will capture snapshots from each working camera")
    print("and open them so you can identify which is which.\n")
    
    # Create output directory
    output_dir = "camera_snapshots"
    os.makedirs(output_dir, exist_ok=True)
    
    snapshots = []
    
    # Test cameras 0-2
    for i in range(3):
        output_path = os.path.join(output_dir, f"camera_{i}.jpg")
        success = capture_snapshot(i, output_path)
        
        if success:
            snapshots.append((i, output_path))
            print(f"   Opening image...")
            open_image(output_path)
            time.sleep(0.5)  # Small delay before next camera
    
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    
    if snapshots:
        print(f"\n✅ Captured {len(snapshots)} snapshots:")
        for idx, path in snapshots:
            print(f"   Camera {idx}: {path}")
        
        print("\n📸 Images should be open in your default image viewer.")
        print("    Look at each image to identify which camera is which.")
        
        print("\n💡 Common layout:")
        print("   Camera 0: Usually the first/default camera")
        print("   Camera 1: Usually external USB camera (might be Logitech)")
        print("   Camera 2: Sometimes internal/integrated camera")
        
        print("\n🎯 Once you identify the Logitech Brio 100:")
        user_input = input("\nWhich camera index is the Logitech Brio 100? (0, 1, or 2): ").strip()
        
        if user_input in ['0', '1', '2']:
            camera_index = int(user_input)
            print(f"\n✅ Great! Setting CAMERA_INDEX={camera_index} as default in backend...")
            print(f"\n   Add this to your backend configuration or .env file:")
            print(f"   CAMERA_INDEX={camera_index}")
            return camera_index
        else:
            print("\n⚠️  Invalid input. Please check the images manually.")
    else:
        print("\n❌ No cameras were able to capture snapshots.")
    
    print(f"\n{'='*60}")
    return None

if __name__ == "__main__":
    result = main()
    if result is not None:
        print(f"\nRecommended: Set camera index {result} in your backend code or environment.")
