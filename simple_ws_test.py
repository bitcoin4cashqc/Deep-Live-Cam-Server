#!/usr/bin/env python3

"""
Simple WebSocket Connection Test

This script tests basic WebSocket connectivity to the server.
Use this to debug connection issues before running the full client.
"""

import asyncio
import websockets
import json
import time

async def simple_connection_test():
    """Test basic WebSocket connection"""
    try:
        print('Attempting connection to ws://localhost:8765...')
        websocket = await asyncio.wait_for(
            websockets.connect('ws://localhost:8765'),
            timeout=5.0
        )
        print('✓ Connected successfully!')
        
        # Send a ping
        ping_msg = json.dumps({'type': 'ping'})
        await websocket.send(ping_msg)
        print('✓ Sent ping message')
        
        # Wait for response
        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
        print(f'✓ Received response: {response}')
        
        await websocket.close()
        print('✓ Connection closed cleanly')
        return True
        
    except asyncio.TimeoutError:
        print('✗ Connection timed out')
        return False
    except ConnectionRefusedError:
        print('✗ Connection refused - is the server running?')
        return False
    except Exception as e:
        print(f'✗ Connection failed: {e}')
        return False

async def detailed_connection_test():
    """Test with more detailed error handling"""
    print('\n--- Detailed Connection Test ---')
    
    try:
        print('Creating connection...')
        websocket = await websockets.connect(
            'ws://localhost:8765',
            ping_interval=None,  # Disable ping
            ping_timeout=None,   # Disable ping timeout
            close_timeout=10
        )
        print('✓ WebSocket connection established')
        
        # Test sending and receiving
        test_msg = json.dumps({
            'type': 'ping',
            'timestamp': time.time(),
            'test': True
        })
        
        await websocket.send(test_msg)
        print('✓ Test message sent')
        
        # Wait for any response
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            print(f'✓ Received: {response}')
        except asyncio.TimeoutError:
            print('! No response received (this might be normal)')
        
        await websocket.close()
        print('✓ Connection closed')
        return True
        
    except Exception as e:
        print(f'✗ Detailed test failed: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print('WebSocket Connection Test')
    print('=' * 40)
    
    # Run basic test
    success1 = asyncio.run(simple_connection_test())
    
    # Run detailed test
    success2 = asyncio.run(detailed_connection_test())
    
    print('\n' + '=' * 40)
    print(f'Basic test: {"PASS" if success1 else "FAIL"}')
    print(f'Detailed test: {"PASS" if success2 else "FAIL"}')
    
    if not (success1 or success2):
        print('\nTroubleshooting:')
        print('1. Ensure server is running: python server_ws.py')
        print('2. Check if port 8765 is listening: ss -tlnp | grep 8765')
        print('3. Try connecting from outside: telnet localhost 8765')