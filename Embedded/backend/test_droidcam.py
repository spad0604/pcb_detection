#!/usr/bin/env python3
"""Quick test to display DroidCam feed."""

import cv2

def main():
    print("Opening DroidCam at /dev/video0...")
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Cannot open camera!")
        return
    
    # Set higher resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
    
    print("✅ Camera opened successfully!")
    print("Press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Cannot read frame")
            break
        
        # Show resolution on frame
        h, w = frame.shape[:2]
        cv2.putText(frame, f"DroidCam: {w}x{h}", (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('DroidCam Test - Press Q to quit', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("Camera test closed.")

if __name__ == "__main__":
    main()
