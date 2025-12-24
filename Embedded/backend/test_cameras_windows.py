#!/usr/bin/env python3
"""Script to test all available cameras on Windows and show their names."""

import cv2
import sys

def get_camera_name_windows(index):
    """Try to get camera name on Windows using DirectShow backend."""
    try:
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap.isOpened():
            # Try to get backend name
            backend = cap.getBackendName()
            cap.release()
            return backend
    except:
        pass
    return "Unknown"

def test_camera(index):
    """Test if a camera at given index works."""
    print(f"\n{'='*60}")
    print(f"Testing Camera Index {index}...")
    print(f"{'='*60}")
    
    try:
        # Try DirectShow first (Windows)
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            print(f"❌ Cannot open camera at index {index}")
            return False, None
        
        # Try to read a frame
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"❌ Camera {index} opened but cannot read frame")
            cap.release()
            return False, None
        
        # Get camera properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        backend = cap.getBackendName()
        
        print(f"✅ Camera {index} is WORKING!")
        print(f"   Backend: {backend}")
        print(f"   Resolution: {width}x{height}")
        print(f"   FPS: {fps}")
        print(f"   Frame shape: {frame.shape}")
        
        cap.release()
        return True, backend
        
    except Exception as e:
        print(f"❌ Error testing camera {index}: {e}")
        return False, None

def main():
    print("🔍 Scanning for available cameras on Windows...")
    print("Looking for DroidCam Video and other cameras...")
    
    working_cameras = []
    camera_info = {}
    
    # Test camera indices 0 through 10 (Windows can have higher indices)
    for i in range(11):
        success, backend = test_camera(i)
        if success:
            working_cameras.append(i)
            camera_info[i] = backend
    
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"{'='*60}")
    if working_cameras:
        print(f"✅ Found {len(working_cameras)} working camera(s):")
        for cam in working_cameras:
            backend = camera_info.get(cam, "Unknown")
            print(f"   Index {cam}: {backend}")
        
        print("\nTo use a specific camera in your .env file or environment:")
        for cam in working_cameras:
            print(f"   CAMERA_INDEX={cam}")
    else:
        print("❌ No working cameras found!")
        print("\nTroubleshooting:")
        print("1. Make sure DroidCam is running on your phone")
        print("2. Check if DroidCam client is connected on Windows")
        print("3. Try opening DroidCam Video in another app (like Camera app)")
    
    print(f"\n{'='*60}")

if __name__ == "__main__":
    main()
