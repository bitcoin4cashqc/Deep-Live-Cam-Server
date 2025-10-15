import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import threading
import queue
import time
from typing import Optional, Callable, Dict, Any
import logging

from modules.video_capture import VideoCapturer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaceSwapClient:
    def __init__(self, server_url: str, camera_index: int = 0, source_face_path: str = None):
        self.server_url = server_url
        self.camera_index = camera_index
        self.source_face_path = source_face_path
        self.source_face_registered = False
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        
        # Video components
        self.video_capturer = VideoCapturer(camera_index)
        self.current_frame: Optional[np.ndarray] = None
        self.processed_frame: Optional[np.ndarray] = None
        
        # Threading and queues
        self.frame_queue = queue.Queue(maxsize=10)
        self.processed_queue = queue.Queue(maxsize=10)
        self.stop_event = threading.Event()
        
        # Callbacks
        self.on_processed_frame: Optional[Callable[[np.ndarray], None]] = None
        self.on_connection_status: Optional[Callable[[bool, str], None]] = None
        self.on_stats_update: Optional[Callable[[Dict[str, Any]], None]] = None
        
        # Statistics
        self.stats = {
            'frames_sent': 0,
            'frames_received': 0,
            'connection_time': 0,
            'fps_sent': 0.0,
            'fps_received': 0.0,
            'last_sent_time': 0,
            'last_received_time': 0
        }
        
        # FPS calculation
        self.sent_times = []
        self.received_times = []
        
    def encode_frame(self, frame: np.ndarray) -> Optional[str]:
        try:
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Convert to base64
            frame_data = base64.b64encode(buffer).decode('utf-8')
            return frame_data
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    def decode_frame(self, frame_data: str) -> Optional[np.ndarray]:
        try:
            # Decode base64 to bytes
            frame_bytes = base64.b64decode(frame_data)
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            
            # Decode image
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            logger.error(f"Error decoding frame: {e}")
            return None
    
    def update_fps_stats(self):
        current_time = time.time()
        
        # Update sent FPS
        self.sent_times = [t for t in self.sent_times if current_time - t <= 1.0]
        self.stats['fps_sent'] = len(self.sent_times)
        
        # Update received FPS
        self.received_times = [t for t in self.received_times if current_time - t <= 1.0]
        self.stats['fps_received'] = len(self.received_times)
    
    async def connect(self) -> bool:
        try:
            logger.info(f"Connecting to WebSocket server: {self.server_url}")
            
            # Add headers to bypass ngrok browser warning
            additional_headers = None
            if 'ngrok' in self.server_url:
                additional_headers = {'ngrok-skip-browser-warning': 'true'}
            
            self.websocket = await websockets.connect(
                self.server_url,
                ping_interval=30,
                ping_timeout=10,
                additional_headers=additional_headers
            )
            
            self.connected = True
            self.reconnect_attempts = 0
            self.stats['connection_time'] = time.time()
            
            logger.info("Connected to WebSocket server")
            
            # Send source face if available
            if self.source_face_path:
                await self.send_source_face()
            
            if self.on_connection_status:
                self.on_connection_status(True, "Connected")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            self.connected = False
            
            if self.on_connection_status:
                self.on_connection_status(False, f"Connection failed: {e}")
            
            return False
    
    async def disconnect(self):
        if self.websocket and self.connected:
            await self.websocket.close()
        
        self.connected = False
        
        if self.on_connection_status:
            self.on_connection_status(False, "Disconnected")
    
    async def send_frame(self, frame: np.ndarray):
        if not self.connected or not self.websocket:
            return
        
        try:
            encoded_frame = self.encode_frame(frame)
            if encoded_frame:
                message = json.dumps({
                    'type': 'frame',
                    'data': encoded_frame,
                    'timestamp': time.time()
                })
                
                await self.websocket.send(message)
                
                # Update statistics
                current_time = time.time()
                self.stats['frames_sent'] += 1
                self.stats['last_sent_time'] = current_time
                self.sent_times.append(current_time)
                
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            logger.warning("Connection closed while sending frame")
        except Exception as e:
            logger.error(f"Error sending frame: {e}")
    
    async def send_source_face(self):
        """Send source face image to server"""
        if not self.connected or not self.websocket or not self.source_face_path:
            return False
        
        try:
            import cv2
            # Load and encode source face image
            face_image = cv2.imread(self.source_face_path)
            if face_image is None:
                logger.error(f"Could not load source face image: {self.source_face_path}")
                return False
            
            encoded_face = self.encode_frame(face_image)
            if not encoded_face:
                logger.error("Failed to encode source face image")
                return False
            
            message = json.dumps({
                'type': 'source_face',
                'data': encoded_face,
                'timestamp': time.time()
            })
            
            await self.websocket.send(message)
            logger.info("Source face sent to server")
            return True
            
        except Exception as e:
            logger.error(f"Error sending source face: {e}")
            return False

    async def request_stats(self):
        if not self.connected or not self.websocket:
            return
        
        try:
            message = json.dumps({'type': 'stats_request'})
            await self.websocket.send(message)
        except Exception as e:
            logger.error(f"Error requesting stats: {e}")
    
    def set_source_face(self, face_path: str):
        """Set a new source face path"""
        self.source_face_path = face_path
        self.source_face_registered = False
    
    async def handle_messages(self):
        if not self.websocket:
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    if data.get('type') == 'processed_frame':
                        frame_data = data.get('data')
                        if frame_data:
                            processed_frame = self.decode_frame(frame_data)
                            if processed_frame is not None:
                                self.processed_frame = processed_frame
                                
                                # Update statistics
                                current_time = time.time()
                                self.stats['frames_received'] += 1
                                self.stats['last_received_time'] = current_time
                                self.received_times.append(current_time)
                                
                                # Callback for processed frame
                                if self.on_processed_frame:
                                    self.on_processed_frame(processed_frame)
                    
                    elif data.get('type') == 'stats':
                        server_stats = data.get('data', {})
                        if self.on_stats_update:
                            self.on_stats_update(server_stats)
                    
                    elif data.get('type') == 'pong':
                        # Server responded to ping, connection is healthy
                        logger.debug("Received pong from server")
                    
                    elif data.get('type') == 'source_face_confirmation':
                        # Server confirmed source face registration
                        status = data.get('status')
                        message = data.get('message', '')
                        
                        if status == 'success':
                            self.source_face_registered = True
                            logger.info(f"Source face registered: {message}")
                            if self.on_connection_status:
                                self.on_connection_status(True, f"Source face registered: {message}")
                        else:
                            self.source_face_registered = False
                            logger.error(f"Source face registration failed: {message}")
                            if self.on_connection_status:
                                self.on_connection_status(False, f"Source face error: {message}")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from server")
                except Exception as e:
                    logger.error(f"Error handling server message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            self.connected = False
            logger.warning("Connection closed by server")
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            self.connected = False
    
    def start_camera_capture(self, width: int = 640, height: int = 480, fps: int = 30) -> bool:
        if not self.video_capturer.start(width, height, fps):
            logger.error("Failed to start camera capture")
            return False
        
        logger.info(f"Camera capture started: {width}x{height} @ {fps}fps")
        return True
    
    def stop_camera_capture(self):
        self.video_capturer.release()
        logger.info("Camera capture stopped")
    
    async def capture_and_send_loop(self, target_fps: int = 30):
        frame_delay = 1.0 / target_fps
        
        while not self.stop_event.is_set() and self.connected:
            try:
                # Capture frame
                ret, frame = self.video_capturer.read()
                if ret and frame is not None:
                    self.current_frame = frame
                    
                    # Send frame to server
                    await self.send_frame(frame)
                
                # Update FPS statistics
                self.update_fps_stats()
                
                # Wait for next frame
                await asyncio.sleep(frame_delay)
                
            except Exception as e:
                logger.error(f"Error in capture loop: {e}")
                await asyncio.sleep(0.1)
    
    async def ping_server(self):
        """Send periodic ping to server to maintain connection"""
        while not self.stop_event.is_set() and self.connected:
            try:
                if self.websocket and self.connected:
                    ping_message = json.dumps({
                        'type': 'ping',
                        'timestamp': time.time()
                    })
                    await self.websocket.send(ping_message)
                    await asyncio.sleep(30)  # Ping every 30 seconds
                else:
                    break
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                self.connected = False
                break

    async def auto_reconnect(self):
        while not self.stop_event.is_set():
            if not self.connected and self.reconnect_attempts < self.max_reconnect_attempts:
                self.reconnect_attempts += 1
                
                # Calculate backoff delay (exponential with jitter)
                import random
                base_delay = min(2 ** self.reconnect_attempts, 60)  # Max 60 seconds
                jitter = random.uniform(0.1, 0.3) * base_delay  # Add 10-30% jitter
                delay = base_delay + jitter
                
                logger.info(f"Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts}) in {delay:.1f}s")
                
                await asyncio.sleep(delay)
                
                if await self.connect():
                    # Reset reconnect attempts on successful connection
                    self.reconnect_attempts = 0
                    # Start message handling and ping tasks
                    asyncio.create_task(self.handle_messages())
                    asyncio.create_task(self.ping_server())
                    
                    if self.on_connection_status:
                        self.on_connection_status(True, f"Reconnected successfully after {self.reconnect_attempts} attempts")
                else:
                    if self.on_connection_status:
                        self.on_connection_status(False, f"Reconnection failed (attempt {self.reconnect_attempts}/{self.max_reconnect_attempts})")
            
            elif self.reconnect_attempts >= self.max_reconnect_attempts:
                logger.error("Maximum reconnection attempts reached. Stopping auto-reconnect.")
                if self.on_connection_status:
                    self.on_connection_status(False, "Maximum reconnection attempts reached")
                break
            
            await asyncio.sleep(5)  # Check every 5 seconds
    
    async def start_client(self, camera_width: int = 640, camera_height: int = 480, camera_fps: int = 30, target_fps: int = 30):
        # Start camera
        if not self.start_camera_capture(camera_width, camera_height, camera_fps):
            return False
        
        # Connect to server
        if not await self.connect():
            self.stop_camera_capture()
            return False
        
        try:
            # Start concurrent tasks
            tasks = [
                asyncio.create_task(self.handle_messages()),
                asyncio.create_task(self.capture_and_send_loop(target_fps)),
                asyncio.create_task(self.auto_reconnect()),
                asyncio.create_task(self.ping_server())
            ]
            
            # Wait for any task to complete
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                
        finally:
            await self.disconnect()
            self.stop_camera_capture()
        
        return True
    
    def stop_client(self):
        self.stop_event.set()
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            'connected': self.connected,
            'reconnect_attempts': self.reconnect_attempts,
            'server_url': self.server_url,
            'camera_index': self.camera_index
        }
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        return self.current_frame
    
    def get_processed_frame(self) -> Optional[np.ndarray]:
        return self.processed_frame


class SimpleVideoClient:
    def __init__(self, server_url: str, camera_index: int = 0, source_face_path: str = None):
        self.client = FaceSwapClient(server_url, camera_index, source_face_path)
        self.display_window = "Deep Live Cam - Client"
        self.running = False
        
        # Set up callbacks
        self.client.on_processed_frame = self._on_processed_frame
        self.client.on_connection_status = self._on_connection_status
    
    def _on_processed_frame(self, frame: np.ndarray):
        if self.running:
            cv2.imshow(self.display_window, frame)
    
    def _on_connection_status(self, connected: bool, message: str):
        status = "Connected" if connected else "Disconnected"
        logger.info(f"Connection status: {status} - {message}")
    
    async def run(self, show_fps: bool = True):
        self.running = True
        
        cv2.namedWindow(self.display_window, cv2.WINDOW_NORMAL)
        
        # Start client in background
        client_task = asyncio.create_task(self.client.start_client())
        
        try:
            while self.running:
                # Check for window close or 'q' key
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or cv2.getWindowProperty(self.display_window, cv2.WND_PROP_VISIBLE) < 1:
                    self.running = False
                    break
                
                # Show current frame if no processed frame available
                if self.client.get_processed_frame() is None:
                    current_frame = self.client.get_current_frame()
                    if current_frame is not None:
                        display_frame = current_frame.copy()
                        
                        if not self.client.connected:
                            cv2.putText(display_frame, "Connecting...", (10, 30), 
                                      cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        
                        cv2.imshow(self.display_window, display_frame)
                
                # Show FPS info
                if show_fps:
                    stats = self.client.get_stats()
                    title = f"Deep Live Cam - Client (Sent: {stats['fps_sent']:.1f}fps, Received: {stats['fps_received']:.1f}fps)"
                    cv2.setWindowTitle(self.display_window, title)
                
                await asyncio.sleep(0.01)
                
        finally:
            self.client.stop_client()
            cv2.destroyAllWindows()
            
            if not client_task.done():
                client_task.cancel()


async def run_simple_client(server_url: str, camera_index: int = 0, source_face_path: str = None):
    client = SimpleVideoClient(server_url, camera_index, source_face_path)
    await client.run()