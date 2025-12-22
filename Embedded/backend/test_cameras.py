#!/usr/bin/env python3
"""Script to test all available cameras and show which ones work."""

import cv2
import sys

def test_camera(index):
    """Test if a camera at given index works."""
    print(f"\n{'='*60}")
    print(f"Testing /dev/video{index}...")
    print(f"{'='*60}")
    
    try:
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            print(f"❌ Cannot open /dev/video{index}")
            return False
        
        # Try to read a frame
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"❌ /dev/video{index} opened but cannot read frame")
            cap.release()
            return False
        
        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"✅ /dev/video{index} is WORKING!")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps}")
        print(f"   Frame shape: {frame.shape}")
        
        # Check device name from sysfs
        try:
            with open(f"/sys/class/video4linux/video{index}/name", "r") as f:
                device_name = f.read().strip()
                print(f"   Device name: {device_name}")
        except:
            pass
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ Error testing /dev/video{index}: {e}")
        return False

def main():
    print("🔍 Scanning for available cameras...")
    print("Looking for your Android phone camera...")
    
    working_cameras = []
    
    # Test video0 through video7
    for i in range(8):
        if test_camera(i):
            working_cameras.append(i)
    
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    if working_cameras:
        print(f"✅ Found {len(working_cameras)} working camera(s): {working_cameras}")
        print("\nTo use a specific camera, set the CAMERA_INDEX environment variable:")
        for cam in working_cameras:
            print(f"  export CAMERA_INDEX={cam}")
    else:
        print("❌ No working cameras found!")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
