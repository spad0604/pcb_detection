#!/usr/bin/env python3
"""Show preview from each camera to identify which is which."""

import cv2
import sys

def show_camera_preview(index):
    """Show live preview from camera at given index."""
    print(f"\n{'='*60}")
    print(f"Opening Camera {index}...")
    print(f"Press 'q' to close and test next camera")
    print(f"{'='*60}\n")
    
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    
    if not cap.isOpened():
        print(f"❌ Cannot open camera {index}")
        return False
    
    ret, test_frame = cap.read()
    if not ret:
        print(f"❌ Camera {index} opened but cannot read frame")
        cap.release()
        return False
    
    print(f"✅ Camera {index} is working!")
    print(f"   Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    print(f"\n🎥 Showing preview... (Press 'q' to close)")
    
    window_name = f"Camera {index} Preview - Press 'q' to close"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Lost camera connection")
            break
        
        # Add text overlay
        text = f"Camera Index: {index}"
        cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                   1, (0, 255, 0), 2, cv2.LINE_AA)
        
        cv2.imshow(window_name, frame)
        
        # Press 'q' to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return True

def main():
    print("="*60)
    print("Camera Preview Tool")
    print("="*60)
    print("\nThis will show you preview from each working camera")
    print("so you can identify which one is which.\n")
    
    # Test cameras
    for i in range(3):
        success = show_camera_preview(i)
        if success:
            response = input(f"\nIs Camera {i} the Logitech Brio 100? (y/n): ").strip().lower()
            if response == 'y':
                print(f"\n✅ Great! Use CAMERA_INDEX={i} in your backend")
                print(f"\nAdd this to your .env file or set environment variable:")
                print(f"   CAMERA_INDEX={i}")
                break
        else:
            print(f"Skipping camera {i}...")
    
    print("\n" + "="*60)
    print("Done!")
    print("="*60)

if __name__ == "__main__":
    main()
