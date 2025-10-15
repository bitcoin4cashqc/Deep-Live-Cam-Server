import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import threading
import queue
import time
from typing import Set, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import logging

import modules.globals
from modules.processors.frame.core import get_frame_processors_modules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FaceSwapServer:
    def __init__(self, port: int = 8765, max_workers: int = 4):
        self.port = port
        self.max_workers = max_workers
        
        # Client management
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.client_info: Dict[websockets.WebSocketServerProtocol, Dict[str, Any]] = {}
        self.client_source_faces: Dict[websockets.WebSocketServerProtocol, Any] = {}  # Store face data per client
        
        # Frame processing queues
        self.raw_frames_queue = queue.Queue(maxsize=50)
        self.processed_frames_queue = queue.Queue(maxsize=50)
        
        # Threading components
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_thread = None
        self.distribution_thread = None
        self.stop_event = threading.Event()
        
        # Statistics
        self.stats = {
            'frames_received': 0,
            'frames_processed': 0,
            'frames_sent': 0,
            'connected_clients': 0,
            'processing_time_avg': 0.0
        }
        
        # Initialize face processors (defer to async method)
        self.frame_processors = []
        self.processors_initialized = False
    
    async def _initialize_processors(self):
        """Initialize processors with yield points to avoid blocking the event loop"""
        if self.processors_initialized:
            return
            
        logger.info("Initializing face processors in background...")
        modules.globals.headless = True
        
        # Initialize frame processors
        self.frame_processors = get_frame_processors_modules(modules.globals.frame_processors)
        
        # Pre-start processors with yield points
        for processor in self.frame_processors:
            logger.info(f"Pre-starting processor: {processor.NAME}")
            if not processor.pre_start():
                raise RuntimeError(f"Failed to initialize processor: {processor.NAME}")
            # Yield control back to event loop after each processor
            await asyncio.sleep(0)
        
        self.processors_initialized = True
        logger.info("Face processors initialized successfully")
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        self.clients.add(websocket)
        self.client_info[websocket] = {
            'connected_at': time.time(),
            'frames_sent': 0,
            'last_frame_time': 0
        }
        self.stats['connected_clients'] = len(self.clients)
        logger.info(f"Client connected. Total clients: {len(self.clients)}")
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        self.clients.discard(websocket)
        if websocket in self.client_info:
            del self.client_info[websocket]
        if websocket in self.client_source_faces:
            del self.client_source_faces[websocket]
        self.stats['connected_clients'] = len(self.clients)
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")
    
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
    
    def encode_frame(self, frame: np.ndarray) -> Optional[str]:
        try:
            # Encode frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            # Convert to base64
            frame_data = base64.b64encode(buffer).decode('utf-8')
            return frame_data
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    def process_frame(self, frame: np.ndarray, client_websocket: websockets.WebSocketServerProtocol) -> Optional[np.ndarray]:
        try:
            start_time = time.time()
            
            # Check if processors are initialized
            if not self.processors_initialized:
                logger.warning("Processors not initialized yet, returning original frame")
                return frame
            
            # Check if client has provided a source face
            if client_websocket not in self.client_source_faces:
                logger.warning("No source face provided by client, returning original frame")
                return frame
            
            source_face = self.client_source_faces[client_websocket]
            processed_frame = frame.copy()
            
            # Apply frame processors with client-specific source face
            for processor in self.frame_processors:
                processed_frame = processor.process_frame(
                    source_face, 
                    processed_frame, 
                    processed_frame
                )
            
            # Update processing time statistics
            processing_time = time.time() - start_time
            self.stats['processing_time_avg'] = (
                self.stats['processing_time_avg'] * 0.9 + processing_time * 0.1
            )
            
            return processed_frame
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
            return None
    
    def frame_processor_worker(self):
        while not self.stop_event.is_set():
            try:
                # Get frame from queue with timeout
                client_websocket, frame = self.raw_frames_queue.get(timeout=1.0)
                
                if frame is not None:
                    # Process the frame with client-specific source face
                    processed_frame = self.process_frame(frame, client_websocket)
                    
                    if processed_frame is not None:
                        # Add to processed queue
                        try:
                            self.processed_frames_queue.put(
                                (client_websocket, processed_frame), 
                                timeout=0.1
                            )
                            self.stats['frames_processed'] += 1
                        except queue.Full:
                            logger.warning("Processed frames queue is full, dropping frame")
                
                self.raw_frames_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in frame processor: {e}")
    
    async def frame_distributor_worker(self):
        while not self.stop_event.is_set():
            try:
                # Get processed frame
                target_client, processed_frame = self.processed_frames_queue.get(timeout=1.0)
                
                if processed_frame is not None:
                    # Encode frame
                    encoded_frame = self.encode_frame(processed_frame)
                    
                    if encoded_frame:
                        # Send only to the specific client who sent the original frame
                        if target_client in self.clients:
                            message = json.dumps({
                                'type': 'processed_frame',
                                'data': encoded_frame,
                                'timestamp': time.time()
                            })
                            
                            try:
                                await target_client.send(message)
                                self.client_info[target_client]['frames_sent'] += 1
                                self.client_info[target_client]['last_frame_time'] = time.time()
                                self.stats['frames_sent'] += 1
                            except websockets.exceptions.ConnectionClosed:
                                await self.unregister_client(target_client)
                            except Exception as e:
                                logger.error(f"Error sending frame to client: {e}")
                                await self.unregister_client(target_client)
                
                self.processed_frames_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in frame distributor: {e}")
            
            await asyncio.sleep(0.001)  # Small delay to prevent busy waiting
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol):
        client_addr = getattr(websocket.remote_address, '__str__', lambda: 'unknown')()
        logger.info(f"New client connection from {client_addr}")
        
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                try:
                    # Validate message size
                    if len(message) > 10 * 1024 * 1024:  # 10MB limit
                        logger.warning(f"Message too large from {client_addr}, dropping")
                        continue
                    
                    data = json.loads(message)
                    message_type = data.get('type')
                    
                    if message_type == 'frame':
                        # Decode and queue frame for processing
                        frame_data = data.get('data')
                        if frame_data:
                            frame = self.decode_frame(frame_data)
                            if frame is not None:
                                try:
                                    self.raw_frames_queue.put(
                                        (websocket, frame), 
                                        timeout=0.01
                                    )
                                    self.stats['frames_received'] += 1
                                except queue.Full:
                                    logger.warning("Raw frames queue is full, dropping frame")
                            else:
                                logger.warning(f"Failed to decode frame from {client_addr}")
                    
                    elif message_type == 'source_face':
                        # Client is sending their source face
                        face_data = data.get('data')
                        if face_data:
                            try:
                                # Decode the source face image
                                face_image = self.decode_frame(face_data)
                                if face_image is not None:
                                    # Extract face features for this client
                                    from modules.face_analyser import get_one_face
                                    face_features = get_one_face(face_image)
                                    if face_features:
                                        self.client_source_faces[websocket] = face_features
                                        logger.info(f"Source face registered for client {client_addr}")
                                        
                                        # Send confirmation
                                        confirmation = json.dumps({
                                            'type': 'source_face_confirmation',
                                            'status': 'success',
                                            'message': 'Source face registered successfully'
                                        })
                                        await websocket.send(confirmation)
                                    else:
                                        logger.warning(f"No face detected in source image from {client_addr}")
                                        error_msg = json.dumps({
                                            'type': 'source_face_confirmation',
                                            'status': 'error',
                                            'message': 'No face detected in source image'
                                        })
                                        await websocket.send(error_msg)
                                else:
                                    logger.warning(f"Failed to decode source face from {client_addr}")
                            except Exception as e:
                                logger.error(f"Error processing source face from {client_addr}: {e}")
                                error_msg = json.dumps({
                                    'type': 'source_face_confirmation',
                                    'status': 'error',
                                    'message': f'Error processing source face: {e}'
                                })
                                await websocket.send(error_msg)
                    
                    elif message_type == 'stats_request':
                        # Send server statistics
                        try:
                            stats_message = json.dumps({
                                'type': 'stats',
                                'data': self.get_stats()
                            })
                            await websocket.send(stats_message)
                        except Exception as e:
                            logger.error(f"Error sending stats to {client_addr}: {e}")
                    
                    elif message_type == 'ping':
                        # Respond to ping with pong
                        try:
                            pong_message = json.dumps({
                                'type': 'pong',
                                'timestamp': time.time()
                            })
                            await websocket.send(pong_message)
                        except Exception as e:
                            logger.error(f"Error sending pong to {client_addr}: {e}")
                    
                    else:
                        logger.warning(f"Unknown message type '{message_type}' from {client_addr}")
                        
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON received from {client_addr}")
                except UnicodeDecodeError:
                    logger.error(f"Invalid encoding received from {client_addr}")
                except Exception as e:
                    logger.error(f"Error handling client message from {client_addr}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {client_addr} disconnected")
        except websockets.exceptions.ConnectionClosedError:
            logger.info(f"Client {client_addr} connection closed unexpectedly")
        except Exception as e:
            logger.error(f"Unexpected error with client {client_addr}: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def start_server(self):
        logger.info(f"Starting WebSocket server on port {self.port}")
        
        # Start the WebSocket server first (minimal setup)
        server = await websockets.serve(
            self.handle_client, 
            "0.0.0.0", 
            self.port,
            ping_interval=30,
            ping_timeout=10
        )
        
        logger.info(f"WebSocket server started on ws://0.0.0.0:{self.port}")
        
        # Start background initialization without blocking
        # asyncio.create_task(self._start_background_services())  # Temporarily disabled for testing
        
        return server
    
    async def _start_background_services(self):
        """Start all background services after server is ready to accept connections"""
        try:
            # Initialize processors in background
            await self._initialize_processors()
            
            # Start processing threads only after processors are ready
            self.processing_thread = threading.Thread(
                target=self.frame_processor_worker, 
                daemon=True
            )
            self.processing_thread.start()
            
            # Start frame distributor
            self.distributor_task = asyncio.create_task(self.frame_distributor_worker())
            
            logger.info("All background services started successfully")
            
        except Exception as e:
            logger.error(f"Error starting background services: {e}")
            raise
    
    def stop_server(self):
        logger.info("Stopping WebSocket server")
        self.stop_event.set()
        
        # Cancel the distributor task
        if hasattr(self, 'distributor_task') and not self.distributor_task.done():
            self.distributor_task.cancel()
        
        if self.processing_thread:
            self.processing_thread.join()
        
        self.executor.shutdown(wait=True)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            'uptime': time.time(),
            'client_details': {
                str(id(client)): info for client, info in self.client_info.items()
            }
        }


async def run_server(port: int = 8765, max_workers: int = 4):
    server = FaceSwapServer(port, max_workers)
    
    try:
        ws_server = await server.start_server()
        # Keep the server running until interrupted
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    finally:
        server.stop_server()
        if ws_server:
            ws_server.close()
            await ws_server.wait_closed()