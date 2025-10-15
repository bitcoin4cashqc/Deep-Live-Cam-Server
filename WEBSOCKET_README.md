# Deep Live Cam - WebSocket Server/Client Mode

This document describes the new WebSocket server/client functionality that enables distributed face swapping across multiple machines.

## Overview

The WebSocket implementation allows you to:
- Run face swapping processing on a powerful GPU server
- Connect multiple clients from different machines
- Stream video in real-time over the network
- Scale processing across multiple clients

## Architecture

```
Client 1 (Webcam) ──┐
                    ├── WebSocket ──→ Server (GPU Processing)
Client 2 (Webcam) ──┘
```

- **Server**: Runs the face swapping processing on GPU
- **Clients**: Capture video, send to server, display processed results

## Quick Start

### 1. Install Dependencies

Make sure you have the WebSocket dependency installed:

```bash
pip install websockets>=11.0
```

### 2. Start the Server (No Face Required)

```bash
# Basic server startup - accepts any client with their own face
python server_ws.py

# Server with custom port and GPU acceleration
python server_ws.py --server-port 9000 --execution-provider cuda

# Server with multiple processing threads
python server_ws.py --execution-threads 8
```

### 3. Connect Clients (Each with Their Own Face)

```bash
# Connect client to local server with your face
python client_ws.py -s my_face.jpg

# Connect to remote server
python client_ws.py -s my_face.jpg --server-url ws://192.168.1.100:8765

# Use specific camera
python client_ws.py -s my_face.jpg --camera-index 1
```

## Usage Examples

### Local Testing

1. Start the server:
```bash
python server_ws.py
```

2. In another terminal, start a client with your face:
```bash
python client_ws.py -s your_face.jpg
```

3. The client window will open showing your webcam with face swapping applied in real-time.

### Remote GPU Server

1. On your GPU server (e.g., 192.168.1.100):
```bash
python server_ws.py --execution-provider cuda
```

2. On client machines (each person uses their own face):
```bash
# Alice's laptop
python client_ws.py -s alice_face.jpg --server-url ws://192.168.1.100:8765

# Bob's laptop  
python client_ws.py -s bob_face.jpg --server-url ws://192.168.1.100:8765
```

### Multiple Clients (Different Faces)

You can connect multiple clients to the same server, each with their own face:

```bash
# Terminal 1 - Person A
python client_ws.py -s person_a_face.jpg --camera-index 0

# Terminal 2 - Person B
python client_ws.py -s person_b_face.jpg --camera-index 1

# Terminal 3 (remote machine) - Person C
python client_ws.py -s person_c_face.jpg --server-url ws://your-server-ip:8765
```

## GUI Integration

The main GUI now includes WebSocket client functionality:

1. Start the GUI: `python run.py`
2. In the WebSocket Client section:
   - Enter server URL (e.g., `ws://192.168.1.100:8765`)
   - Select camera
   - Click "Connect"
3. Use "Server Status" button to monitor server performance

## Command Line Options

### Server Options

```bash
python server_ws.py [options]

Required:
  -s, --source PATH          Source face image

Optional:
  --server-port PORT         WebSocket server port (default: 8765)
  --execution-provider TYPE  CPU/CUDA/etc (default: cpu)
  --execution-threads N      Processing threads (default: 4)
  --frame-processor TYPE     face_swapper, face_enhancer
```

### Client Options

```bash
python client_ws.py [options]

Optional:
  --server-url URL          WebSocket server URL (default: ws://localhost:8765)
  --camera-index N          Camera index (default: 0)
```

### Core Integration

You can also use WebSocket modes through the main script:

```bash
# Server mode
python run.py --server -s face.jpg --server-port 8765

# Client mode  
python run.py --client --server-url ws://server:8765 --camera-index 0
```

## Performance Tuning

### Server Performance

- **GPU Acceleration**: Use `--execution-provider cuda` for NVIDIA GPUs
- **Processing Threads**: Increase `--execution-threads` for more concurrent processing
- **Memory**: Ensure adequate GPU memory for multiple clients

### Network Optimization

- **Local Network**: Use gigabit ethernet for best performance
- **Quality vs Bandwidth**: Frames are JPEG compressed (85% quality by default)
- **Frame Rate**: Default 30 FPS, can be adjusted in client code

### Client Performance

- **Camera Resolution**: Default 640x480, higher resolutions increase bandwidth
- **Frame Rate**: Balance between smoothness and network load

## Monitoring

### Server Status

Use the GUI's "Server Status" button or connect programmatically:

```python
import asyncio
import websockets
import json

async def get_server_stats():
    async with websockets.connect("ws://localhost:8765") as websocket:
        await websocket.send(json.dumps({'type': 'stats_request'}))
        response = await websocket.recv()
        stats = json.loads(response)
        print(stats)

asyncio.run(get_server_stats())
```

### Multi-Client Testing

Test server capacity:

```bash
python test_multiclient.py 5  # Test with 5 concurrent clients
```

## Troubleshooting

### Connection Issues

1. **Server not starting**:
   - Check if port is already in use
   - Ensure source face image exists
   - Check firewall settings

2. **Client can't connect**:
   - Verify server URL and port
   - Check network connectivity
   - Ensure server is running

3. **Poor performance**:
   - Use GPU acceleration on server
   - Reduce client frame rate
   - Check network bandwidth

### Error Messages

- **"Source path is required"**: Server needs a face image (`-s face.jpg`)
- **"Failed to start camera"**: Check camera index and permissions
- **"Connection refused"**: Server not running or wrong URL/port

## Technical Details

### Protocol

The WebSocket protocol uses JSON messages:

```json
// Client sends frame
{
  "type": "frame",
  "data": "base64_encoded_jpeg",
  "timestamp": 1234567890.123
}

// Server sends processed frame
{
  "type": "processed_frame", 
  "data": "base64_encoded_jpeg",
  "timestamp": 1234567890.123
}

// Stats request/response
{
  "type": "stats_request"
}

{
  "type": "stats",
  "data": {
    "connected_clients": 2,
    "frames_processed": 1234,
    "processing_time_avg": 0.045
  }
}
```

### Security Considerations

- WebSocket connections are unencrypted by default
- For production use, consider WSS (WebSocket Secure)
- Implement authentication if needed
- Use firewalls to restrict server access

## Integration with Original Features

The WebSocket functionality is designed to be complementary:

- **Backward Compatibility**: Original functionality remains unchanged
- **UI Integration**: WebSocket controls added to existing GUI
- **Same Processing**: Uses identical face swapping algorithms
- **Configuration**: Inherits all existing settings and options

## Future Enhancements

Potential improvements:
- WSS (secure WebSocket) support
- Authentication and user management
- Load balancing across multiple servers
- Recording and playback capabilities
- Mobile client applications