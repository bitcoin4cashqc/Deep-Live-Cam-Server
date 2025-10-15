#!/usr/bin/env python3

"""
WebSocket Client Entry Point for Deep Live Cam

This script starts the WebSocket client that captures video from a camera,
sends frames to a WebSocket server for face swapping, and displays the results.

Usage:
    python client_ws.py -s <source_face_image> [options]

Examples:
    # Connect to default server with your face
    python client_ws.py -s my_face.jpg
    
    # Connect to custom server
    python client_ws.py -s my_face.jpg --server-url ws://192.168.1.100:8765
    
    # Use specific camera
    python client_ws.py -s my_face.jpg --camera-index 1
    
    # Full customization
    python client_ws.py -s my_face.jpg --server-url ws://server.example.com:9000 --camera-index 0

Controls:
    - Press 'q' to quit the client
    - Close the video window to quit
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the tkinter fix to patch the ScreenChanged error
import tkinter_fix

from modules import core

if __name__ == '__main__':
    # Force client mode
    if '--client' not in sys.argv:
        sys.argv.extend(['--client'])
    
    # Set default server URL if not specified
    if '--server-url' not in sys.argv:
        sys.argv.extend(['--server-url', 'ws://localhost:8765'])
    
    # Set default camera index if not specified
    if '--camera-index' not in sys.argv:
        sys.argv.extend(['--camera-index', '0'])
    
    # Check if source face is provided
    if '-s' not in sys.argv and '--source' not in sys.argv:
        print("Error: Source face image is required for client mode.")
        print("Usage: python client_ws.py -s <source_face_image> [options]")
        print("\nExamples:")
        print("  python client_ws.py -s my_face.jpg")
        print("  python client_ws.py -s my_face.jpg --server-url ws://192.168.1.100:8765")
        print("  python client_ws.py -s my_face.jpg --camera-index 1")
        sys.exit(1)
    
    print("Deep Live Cam - WebSocket Client")
    print("================================")
    
    # Extract parameters for display
    server_url = 'ws://localhost:8765'
    camera_index = 0
    source_face = None
    
    for i, arg in enumerate(sys.argv):
        if arg == '--server-url' and i + 1 < len(sys.argv):
            server_url = sys.argv[i + 1]
        elif arg == '--camera-index' and i + 1 < len(sys.argv):
            camera_index = sys.argv[i + 1]
        elif (arg == '-s' or arg == '--source') and i + 1 < len(sys.argv):
            source_face = sys.argv[i + 1]
    
    print(f"Server URL: {server_url}")
    print(f"Camera Index: {camera_index}")
    print(f"Source Face: {source_face}")
    print("\nControls:")
    print("  - Press 'q' to quit")
    print("  - Close the video window to quit")
    print("\nStarting client...")
    
    try:
        core.run()
    except KeyboardInterrupt:
        print("\nClient stopped by user.")
    except Exception as e:
        print(f"Client error: {e}")
        sys.exit(1)