#!/usr/bin/env python3

"""
Minimal WebSocket Server Test

This creates a bare-bones WebSocket server to test if the issue
is with the websockets library or the Deep Live Cam server code.
"""

import asyncio
import websockets
import json
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def simple_handler(websocket, path):
    """Simple WebSocket handler that echoes messages"""
    client_addr = websocket.remote_address
    logger.info(f"Client connected from {client_addr}")
    
    try:
        await websocket.send(json.dumps({
            'type': 'connection_confirmed',
            'message': 'Connected to debug server'
        }))
        
        async for message in websocket:
            logger.info(f"Received from {client_addr}: {message}")
            
            try:
                data = json.loads(message)
                response = {
                    'type': 'echo',
                    'original': data,
                    'message': f'Echo from server at {client_addr}'
                }
                await websocket.send(json.dumps(response))
                logger.info(f"Sent echo to {client_addr}")
                
            except json.JSONDecodeError:
                error_response = {
                    'type': 'error',
                    'message': 'Invalid JSON received'
                }
                await websocket.send(json.dumps(error_response))
                
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Client {client_addr} disconnected")
    except Exception as e:
        logger.error(f"Error with client {client_addr}: {e}")
    finally:
        logger.info(f"Handler finished for {client_addr}")

async def main():
    """Start the debug server"""
    print("Starting minimal WebSocket debug server...")
    logger.info("Debug server starting on localhost:8765")
    
    try:
        # Start server
        server = await websockets.serve(
            simple_handler,
            "localhost",
            8765,
            ping_interval=30,
            ping_timeout=10
        )
        
        print("✓ Debug server started on ws://localhost:8765")
        logger.info("Server is ready to accept connections")
        
        # Keep running
        await asyncio.Future()  # Run forever
        
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nDebug server stopped by user")
    except Exception as e:
        print(f"Server failed: {e}")