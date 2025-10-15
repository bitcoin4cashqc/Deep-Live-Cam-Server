#!/usr/bin/env python3

"""
Reduced FPS Client Test

Test client that sends frames at a lower rate for better quality processing.
"""

import asyncio
import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from modules.websocket_client import FaceSwapClient

async def main():
    # Create client with rate limiting
    client = FaceSwapClient(
        server_url="ws://213.173.110.197:28286",
        camera_index=0,
        source_face_path="elon.png"
    )
    
    # Monkey patch to reduce frame rate
    original_send_frame = client._send_frame_to_server
    
    async def rate_limited_send_frame(frame):
        await original_send_frame(frame)
        # Wait between frames for 10 FPS instead of 30 FPS
        await asyncio.sleep(0.1)  # 10 FPS
    
    client._send_frame_to_server = rate_limited_send_frame
    
    print("Starting reduced FPS client (10 FPS)...")
    print("This should give better face swapping quality")
    
    try:
        await client.start_client()
    except KeyboardInterrupt:
        print("\nStopped by user")

if __name__ == "__main__":
    asyncio.run(main())