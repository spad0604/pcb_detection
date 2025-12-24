#!/usr/bin/env python3
"""List all available cameras on Windows with detailed information."""

import cv2
import subprocess
import re

def list_cameras_ffmpeg():
    """Use ffmpeg to list DirectShow devices."""
    print("🔍 Listing cameras using DirectShow...\n")
    try:
        # Run ffmpeg to list dshow devices
        result = subprocess.run(
            ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        output = result.stderr
        
        # Parse video devices
        video_devices = []
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'DirectShow video devices' in line:
                # Parse following lines for device names
                for j in range(i+1, len(lines)):
                    match = re.search(r'"([^"]+)"', lines[j])
                    if match:
                        device_name = match.group(1)
                        video_devices.append(device_name)
                    elif 'DirectShow audio devices' in lines[j]:
                        break
                break
        
        if video_devices:
            print("📹 Found cameras via DirectShow:")
            for idx, name in enumerate(video_devices):
                print(f"   {idx}: {name}")
            return video_devices
        else:
            print("❌ No cameras found via ffmpeg")
            return []
            
    except FileNotFoundError:
        print("⚠️  ffmpeg not found, trying manual OpenCV scan...")
        return []
    except Exception as e:
        print(f"❌ Error listing with ffmpeg: {e}")
        return []

def test_camera_detailed(index):
    """Test camera with detailed error reporting."""
    try:
        # Try with DSHOW backend
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        
        if not cap.isOpened():
            # Try without DSHOW
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                return None
        
        # Try to read frame
        ret, frame = cap.read()
        
        info = {
            'index': index,
            'opened': cap.isOpened(),
            'can_read': ret and frame is not None,
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if ret else 0,
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if ret else 0,
            'fps': cap.get(cv2.CAP_PROP_FPS) if ret else 0,
            'backend': cap.getBackendName()
        }
        
        cap.release()
        return info
        
    except Exception as e:
        return {'index': index, 'error': str(e)}

def main():
    print("="*70)
    print("Windows Camera Detection Tool")
    print("="*70 + "\n")
    
    # Try ffmpeg first
    camera_names = list_cameras_ffmpeg()
    
    print("\n" + "="*70)
    print("Testing cameras with OpenCV...")
    print("="*70 + "\n")
    
    working = []
    partially_working = []
    
    # Test indices 0-10
    for i in range(11):
        info = test_camera_detailed(i)
        
        if info and 'error' not in info:
            if info['can_read']:
                working.append(info)
                print(f"✅ Camera {i}: WORKING")
                print(f"   Backend: {info['backend']}")
                print(f"   Resolution: {info['width']}x{info['height']}")
                print(f"   FPS: {info['fps']}\n")
            elif info['opened']:
                partially_working.append(info)
                print(f"⚠️  Camera {i}: Opens but cannot read frames")
                print(f"   Backend: {info['backend']}\n")
    
    print("="*70)
    print("SUMMARY")
    print("="*70)
    
    if camera_names:
        print(f"\n📹 Camera names from DirectShow:")
        for idx, name in enumerate(camera_names):
            print(f"   Index {idx}: {name}")
    
    print(f"\n✅ Fully working cameras: {len(working)}")
    for cam in working:
        print(f"   Index {cam['index']}: {cam['width']}x{cam['height']} @ {cam['fps']} fps")
    
    if partially_working:
        print(f"\n⚠️  Partially working cameras: {len(partially_working)}")
        for cam in partially_working:
            print(f"   Index {cam['index']}: Opens but no frames")
    
    print("\n💡 Recommendations:")
    if len(camera_names) == 3:
        print("   Based on your system, you have 3 cameras:")
        print("   - DroidCam Video (likely index 0 or 1)")
        print("   - Brio 100 Logitech (likely index 0 or 1)")  
        print("   - Integrated Camera (likely index 2)")
        print("\n   Try each index in your backend to see which is which!")
    
    if working:
        print(f"\n   Set in backend: CAMERA_INDEX=0  (or 1, 2, etc.)")
    
    print("\n" + "="*70)

if __name__ == "__main__":
    main()
