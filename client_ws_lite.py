#!/usr/bin/env python3

"""
Lightweight WebSocket Client Entry Point for Deep Live Cam

This script provides a minimal client that doesn't require heavy ML dependencies.
Perfect for laptop clients that only need to send frames to a remote server.

Usage:
    python client_ws_lite.py -s face.jpg --server-url ws://server:8765

Examples:
    # Connect to local server
    python client_ws_lite.py -s alice.jpg
    
    # Connect to remote server
    python client_ws_lite.py -s bob.jpg --server-url ws://192.168.1.100:8765
    
    # Use different camera
    python client_ws_lite.py -s face.jpg --camera-index 1
"""

import sys
import os
import argparse
import asyncio

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.websocket_client import FaceSwapClient

def parse_args():
    """Parse command line arguments for lightweight client."""
    parser = argparse.ArgumentParser(description='Deep Live Cam - WebSocket Client (Lightweight)')
    parser.add_argument('-s', '--source', required=True, help='source face image path', dest='source_path')
    parser.add_argument('--server-url', help='WebSocket server URL', dest='server_url', default='ws://localhost:8765')
    parser.add_argument('--camera-index', help='camera index', dest='camera_index', type=int, default=0)
    parser.add_argument('-v', '--version', action='version', version='Deep Live Cam Client 1.0')
    
    return parser.parse_args()

async def main():
    """Main client function."""
    args = parse_args()
    
    # Validate source face exists
    if not os.path.exists(args.source_path):
        print(f"Error: Source face image not found: {args.source_path}")
        sys.exit(1)
    
    print("Deep Live Cam - WebSocket Client")
    print("================================")
    print(f"Source Face: {args.source_path}")
    print(f"Server URL: {args.server_url}")
    print(f"Camera Index: {args.camera_index}")
    print()
    
    # Create and start client
    client = FaceSwapClient(
        server_url=args.server_url,
        camera_index=args.camera_index,
        source_face_path=args.source_path
    )
    
    try:
        print("Starting client... Press Ctrl+C to stop.")
        await client.start_client()
    except KeyboardInterrupt:
        print("\nClient stopped by user.")
    except Exception as e:
        print(f"Client error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)