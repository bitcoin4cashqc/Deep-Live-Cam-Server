#!/usr/bin/env python3

"""
WebSocket Server Entry Point for Deep Live Cam

This script starts the WebSocket server for distributed face swapping.
The server processes frames sent by clients using each client's own source face.

Usage:
    python server_ws.py [options]

Examples:
    # Start server with default settings
    python server_ws.py
    
    # Start server on custom port with GPU acceleration
    python server_ws.py --server-port 9000 --execution-provider cuda
    
    # Start server with multiple processing threads
    python server_ws.py --execution-threads 8

Features:
    - Each client can use their own source face
    - Multiple clients can connect simultaneously
    - Clients send their source face when connecting
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# GPU optimizations - set before importing modules
if any('cuda' in arg.lower() for arg in sys.argv):
    os.environ['OMP_NUM_THREADS'] = '1'  # Single thread doubles CUDA performance
    os.environ['MKL_NUM_THREADS'] = '1'  # Optimize MKL for CUDA
    os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'  # TensorFlow GPU memory growth

from modules import core

if __name__ == '__main__':
    # Force server mode
    if '--server' not in sys.argv:
        sys.argv.extend(['--server'])
    
    # Ensure headless mode
    if '--headless' not in sys.argv:
        sys.argv.extend(['--headless'])
    
    # Set default server port if not specified
    if '--server-port' not in sys.argv:
        sys.argv.extend(['--server-port', '8765'])
    
    # Ensure CUDA execution provider is set for GPU acceleration
    if '--execution-provider' not in sys.argv:
        sys.argv.extend(['--execution-provider', 'cuda'])
    
    # Add quality settings for better face swapping
    if '--mouth-mask' not in sys.argv:
        sys.argv.append('--mouth-mask')
    
    if '--keep-fps' not in sys.argv:
        sys.argv.append('--keep-fps')
    
    if '--video-quality' not in sys.argv:
        sys.argv.extend(['--video-quality', '0'])  # 0 = highest quality
    
    print("Deep Live Cam - WebSocket Server")
    print("==================================")
    print("Server starting - clients will provide their own source faces")
    print(f"Port: {8765 if '--server-port' not in sys.argv else 'custom'}")
    print(f"Execution Provider: {'CPU' if '--execution-provider' not in sys.argv else 'custom'}")
    print("Quality Settings: mouth-mask, keep-fps, max video quality enabled")
    print("Each client can connect with their own face to swap")
    
    try:
        core.run()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    except Exception as e:
        print(f"Server error: {e}")
        sys.exit(1)