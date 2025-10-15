#!/usr/bin/env python3

"""
Multi-Client Test Script for Deep Live Cam WebSocket Server

This script tests the server's ability to handle multiple concurrent clients.
It creates virtual clients that send test frames to the server.

Usage:
    # First, start the server in another terminal:
    python server_ws.py
    
    # Then run this test:
    python test_multiclient.py [number_of_clients]

Examples:
    python test_multiclient.py 3    # Test with 3 clients
    python test_multiclient.py      # Test with 2 clients (default)

Note: Each test client will create a unique test face image automatically.
"""

import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import time
import sys


class TestClient:
    def __init__(self, client_id: int, server_url: str = "ws://localhost:8765"):
        self.client_id = client_id
        self.server_url = server_url
        self.frames_sent = 0
        self.frames_received = 0
        self.start_time = None
        self.websocket = None
        self.running = False
    
    def create_test_source_face(self, width: int = 200, height: int = 200) -> np.ndarray:
        """Create a unique test source face for this client"""
        # Create a colored face-like image
        face_color = (
            (self.client_id * 40 + 100) % 155 + 100,  # Keep colors in reasonable range
            (self.client_id * 60 + 80) % 155 + 100,
            (self.client_id * 90 + 120) % 155 + 100
        )
        face_image = np.full((height, width, 3), face_color, dtype=np.uint8)
        
        # Draw a simple face shape
        center = (width // 2, height // 2)
        
        # Face outline (circle)
        cv2.circle(face_image, center, min(width, height) // 3, (255, 255, 255), 2)
        
        # Eyes
        eye_y = center[1] - 20
        cv2.circle(face_image, (center[0] - 25, eye_y), 8, (0, 0, 0), -1)
        cv2.circle(face_image, (center[0] + 25, eye_y), 8, (0, 0, 0), -1)
        
        # Mouth
        mouth_y = center[1] + 30
        cv2.ellipse(face_image, (center[0], mouth_y), (20, 10), 0, 0, 180, (0, 0, 0), 2)
        
        # Client ID
        cv2.putText(face_image, f"C{self.client_id}", (center[0] - 15, center[1] + 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return face_image

    def create_test_frame(self, width: int = 640, height: int = 480) -> np.ndarray:
        """Create a test frame with client ID overlay"""
        # Create a random colored frame
        color = (
            (self.client_id * 50) % 255,
            (self.client_id * 80) % 255,
            (self.client_id * 120) % 255
        )
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        
        # Add client ID text
        cv2.putText(frame, f"Client {self.client_id}", (50, 100), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # Add frame counter
        cv2.putText(frame, f"Frame: {self.frames_sent}", (50, 150), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Add timestamp
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        cv2.putText(frame, timestamp, (50, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return frame
    
    def encode_frame(self, frame: np.ndarray) -> str:
        """Encode frame to base64"""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return base64.b64encode(buffer).decode('utf-8')
    
    async def connect(self) -> bool:
        """Connect to WebSocket server"""
        try:
            print(f"Client {self.client_id}: Connecting to {self.server_url}")
            self.websocket = await websockets.connect(self.server_url)
            print(f"Client {self.client_id}: Connected successfully")
            
            # Send source face
            await self.send_source_face()
            
            return True
        except Exception as e:
            print(f"Client {self.client_id}: Connection failed: {e}")
            return False
    
    async def send_source_face(self):
        """Send test source face to server"""
        if not self.websocket:
            return
        
        try:
            # Create and encode test source face
            source_face = self.create_test_source_face()
            encoded_face = self.encode_frame(source_face)
            
            # Send source face to server
            message = json.dumps({
                'type': 'source_face',
                'data': encoded_face,
                'timestamp': time.time(),
                'client_id': self.client_id
            })
            
            await self.websocket.send(message)
            print(f"Client {self.client_id}: Source face sent to server")
            
        except Exception as e:
            print(f"Client {self.client_id}: Error sending source face: {e}")
    
    async def send_frames(self, duration: int = 30, fps: int = 10):
        """Send test frames for specified duration"""
        if not self.websocket:
            return
        
        frame_delay = 1.0 / fps
        end_time = time.time() + duration
        
        print(f"Client {self.client_id}: Starting to send frames at {fps} FPS for {duration}s")
        
        while time.time() < end_time and self.running:
            try:
                # Create and encode test frame
                frame = self.create_test_frame()
                encoded_frame = self.encode_frame(frame)
                
                # Send frame to server
                message = json.dumps({
                    'type': 'frame',
                    'data': encoded_frame,
                    'timestamp': time.time(),
                    'client_id': self.client_id
                })
                
                await self.websocket.send(message)
                self.frames_sent += 1
                
                # Small delay to maintain FPS
                await asyncio.sleep(frame_delay)
                
            except websockets.exceptions.ConnectionClosed:
                print(f"Client {self.client_id}: Connection closed by server")
                break
            except Exception as e:
                print(f"Client {self.client_id}: Error sending frame: {e}")
                break
    
    async def receive_frames(self):
        """Receive processed frames from server"""
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    if data.get('type') == 'processed_frame':
                        self.frames_received += 1
                        
                        # Log every 10th frame received
                        if self.frames_received % 10 == 0:
                            print(f"Client {self.client_id}: Received {self.frames_received} processed frames")
                    
                    elif data.get('type') == 'source_face_confirmation':
                        status = data.get('status')
                        message = data.get('message', '')
                        if status == 'success':
                            print(f"Client {self.client_id}: ✅ Source face registered - {message}")
                        else:
                            print(f"Client {self.client_id}: ❌ Source face error - {message}")
                    
                    elif data.get('type') == 'stats':
                        stats = data.get('data', {})
                        print(f"Client {self.client_id}: Server stats - "
                              f"Connected: {stats.get('connected_clients', 0)}, "
                              f"Processed: {stats.get('frames_processed', 0)}")
                
                except json.JSONDecodeError:
                    print(f"Client {self.client_id}: Invalid JSON received")
                except Exception as e:
                    print(f"Client {self.client_id}: Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {self.client_id}: Receive connection closed")
        except Exception as e:
            print(f"Client {self.client_id}: Error in receive loop: {e}")
    
    async def request_stats(self):
        """Request server statistics"""
        if self.websocket:
            try:
                stats_request = json.dumps({'type': 'stats_request'})
                await self.websocket.send(stats_request)
            except Exception as e:
                print(f"Client {self.client_id}: Error requesting stats: {e}")
    
    async def run_test(self, duration: int = 30, fps: int = 10):
        """Run the complete test for this client"""
        if not await self.connect():
            return
        
        self.running = True
        self.start_time = time.time()
        
        try:
            # Start concurrent tasks
            tasks = [
                asyncio.create_task(self.send_frames(duration, fps)),
                asyncio.create_task(self.receive_frames())
            ]
            
            # Request stats every 10 seconds
            async def periodic_stats():
                while self.running:
                    await asyncio.sleep(10)
                    await self.request_stats()
            
            tasks.append(asyncio.create_task(periodic_stats()))
            
            # Wait for send_frames to complete
            await tasks[0]
            self.running = False
            
            # Cancel other tasks
            for task in tasks[1:]:
                task.cancel()
            
        finally:
            if self.websocket:
                await self.websocket.close()
        
        # Print final stats
        elapsed = time.time() - self.start_time
        print(f"Client {self.client_id}: Test completed")
        print(f"  Duration: {elapsed:.1f}s")
        print(f"  Frames sent: {self.frames_sent}")
        print(f"  Frames received: {self.frames_received}")
        print(f"  Avg send rate: {self.frames_sent / elapsed:.1f} FPS")
        print(f"  Avg receive rate: {self.frames_received / elapsed:.1f} FPS")


async def run_multi_client_test(num_clients: int = 2, duration: int = 30, fps: int = 10):
    """Run multi-client test"""
    print(f"Starting multi-client test with {num_clients} clients")
    print(f"Test duration: {duration}s, Target FPS per client: {fps}")
    print("=" * 60)
    
    # Create clients
    clients = [TestClient(i + 1) for i in range(num_clients)]
    
    # Start all clients concurrently
    tasks = [client.run_test(duration, fps) for client in clients]
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    
    print("=" * 60)
    print("Multi-client test completed!")
    
    # Print summary
    total_sent = sum(client.frames_sent for client in clients)
    total_received = sum(client.frames_received for client in clients)
    
    print(f"Summary:")
    print(f"  Total frames sent: {total_sent}")
    print(f"  Total frames received: {total_received}")
    print(f"  Overall success rate: {(total_received / total_sent * 100) if total_sent > 0 else 0:.1f}%")


if __name__ == "__main__":
    # Parse command line arguments
    num_clients = 2
    if len(sys.argv) > 1:
        try:
            num_clients = int(sys.argv[1])
            if num_clients < 1 or num_clients > 10:
                print("Number of clients should be between 1 and 10")
                sys.exit(1)
        except ValueError:
            print("Invalid number of clients")
            sys.exit(1)
    
    print("Deep Live Cam - Multi-Client Test")
    print("Make sure the server is running: python server_ws.py")
    print("Each test client will use a unique generated source face.")
    print()
    
    try:
        asyncio.run(run_multi_client_test(num_clients, duration=30, fps=5))
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)