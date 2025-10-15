#!/usr/bin/env python3

"""
Lightweight WebSocket Client Entry Point for Deep Live Cam

This script provides a minimal client that doesn't require heavy ML dependencies.
Perfect for laptop clients that only need to send frames to a remote server.
Includes both GUI and CLI modes.

Usage:
    # GUI Mode (default if no source provided)
    python client_ws_lite.py --gui
    python client_ws_lite.py
    
    # CLI Mode
    python client_ws_lite.py -s face.jpg --server-url ws://server:8765

Examples:
    # Start GUI mode
    python client_ws_lite.py --gui
    
    # CLI mode - Connect to local server
    python client_ws_lite.py -s alice.jpg
    
    # CLI mode - Connect to remote server
    python client_ws_lite.py -s bob.jpg --server-url ws://192.168.1.100:8765
    
    # CLI mode - Use different camera
    python client_ws_lite.py -s face.jpg --camera-index 1
    
    # GUI mode with pre-filled values
    python client_ws_lite.py -s face.jpg --gui
"""

import sys
import os
import argparse
import asyncio
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the tkinter fix to patch the ScreenChanged error
import tkinter_fix

from modules.websocket_client import FaceSwapClient

class ClientGUI:
    """Simple tkinter GUI for the WebSocket client."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Deep Live Cam - WebSocket Client")
        self.root.geometry("400x300")
        self.root.resizable(True, True)
        
        self.client = None
        self.client_task = None
        self.is_running = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the GUI elements."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Source face selection
        ttk.Label(main_frame, text="Source Face Image:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(main_frame, textvariable=self.source_var, width=40)
        self.source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)
        ttk.Button(main_frame, text="Browse", command=self.browse_source).grid(row=0, column=2, padx=(5, 0), pady=5)
        
        # Server URL
        ttk.Label(main_frame, text="Server URL:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.server_var = tk.StringVar(value="ws://localhost:8765")
        ttk.Entry(main_frame, textvariable=self.server_var, width=40).grid(row=1, column=1, columnspan=2, sticky=(tk.W, tk.E), padx=(5, 0), pady=5)
        
        # Camera index
        ttk.Label(main_frame, text="Camera Index:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.camera_var = tk.StringVar(value="0")
        ttk.Entry(main_frame, textvariable=self.camera_var, width=10).grid(row=2, column=1, sticky=tk.W, padx=(5, 0), pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=20)
        
        self.start_button = ttk.Button(button_frame, text="Start Client", command=self.start_client)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop Client", command=self.stop_client, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Status text
        ttk.Label(main_frame, text="Status:").grid(row=4, column=0, sticky=tk.W, pady=(10, 0))
        self.status_text = tk.Text(main_frame, height=8, width=50)
        self.status_text.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Scrollbar for status text
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        scrollbar.grid(row=5, column=3, sticky=(tk.N, tk.S), pady=5)
        self.status_text.configure(yscrollcommand=scrollbar.set)
        
        # Configure text area to expand
        main_frame.rowconfigure(5, weight=1)
        
    def browse_source(self):
        """Open file dialog to select source face image."""
        filename = filedialog.askopenfilename(
            title="Select Source Face Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"), ("All files", "*.*")]
        )
        if filename:
            self.source_var.set(filename)
    
    def log_status(self, message):
        """Add a message to the status text area."""
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def start_client(self):
        """Start the WebSocket client."""
        source_path = self.source_var.get().strip()
        server_url = self.server_var.get().strip()
        camera_index = self.camera_var.get().strip()
        
        # Validate inputs
        if not source_path:
            messagebox.showerror("Error", "Please select a source face image.")
            return
            
        if not os.path.exists(source_path):
            messagebox.showerror("Error", f"Source face image not found: {source_path}")
            return
            
        try:
            camera_idx = int(camera_index)
        except ValueError:
            messagebox.showerror("Error", "Camera index must be a number.")
            return
        
        # Clear status and start client
        self.status_text.delete(1.0, tk.END)
        self.log_status("Starting WebSocket client...")
        self.log_status(f"Source Face: {source_path}")
        self.log_status(f"Server URL: {server_url}")
        self.log_status(f"Camera Index: {camera_idx}")
        # Create client
        self.client = FaceSwapClient(
            server_url=server_url,
            camera_index=camera_idx,
            source_face_path=source_path
        )
        
        # Start client in background thread
        self.is_running = True
        self.client_thread = threading.Thread(target=self.run_client, daemon=True)
        self.client_thread.start()
        
        # Update button states
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
    
    def run_client(self):
        """Run the client in an asyncio event loop."""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the client
            loop.run_until_complete(self.client.start_client())
            
        except Exception as e:
            self.root.after(0, lambda: self.log_status(f"Client error: {e}"))
        finally:
            self.root.after(0, self.client_stopped)
    
    def stop_client(self):
        """Stop the WebSocket client."""
        self.is_running = False
        if self.client:
            # Signal the client to stop
            try:
                # This will cause the client's main loop to exit
                self.log_status("Stopping client...")
            except:
                pass
        
        # Update button states
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
    
    def client_stopped(self):
        """Called when the client has stopped."""
        self.log_status("Client stopped.")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.is_running = False
    
    def run(self):
        """Start the GUI main loop."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.stop_client()

def parse_args():
    """Parse command line arguments for lightweight client."""
    parser = argparse.ArgumentParser(description='Deep Live Cam - WebSocket Client (Lightweight)')
    parser.add_argument('-s', '--source', help='source face image path', dest='source_path')
    parser.add_argument('--server-url', help='WebSocket server URL', dest='server_url', default='ws://localhost:8765')
    parser.add_argument('--camera-index', help='camera index', dest='camera_index', type=int, default=0)
    parser.add_argument('--gui', help='start GUI mode', action='store_true', dest='gui_mode')
    parser.add_argument('-v', '--version', action='version', version='Deep Live Cam Client 1.0')
    
    return parser.parse_args()

async def main_cli(args):
    """Main CLI client function."""
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

def main():
    """Main entry point - choose between GUI and CLI mode."""
    args = parse_args()
    
    # Check if GUI mode is requested or no source is provided (default to GUI)
    if args.gui_mode or not args.source_path:
        # Start GUI mode
        print("Starting Deep Live Cam WebSocket Client - GUI Mode")
        gui = ClientGUI()
        
        # If source was provided via CLI, pre-fill it
        if args.source_path:
            gui.source_var.set(args.source_path)
        if args.server_url != 'ws://localhost:8765':
            gui.server_var.set(args.server_url)
        if args.camera_index != 0:
            gui.camera_var.set(str(args.camera_index))
            
        gui.run()
    else:
        # Start CLI mode
        if not args.source_path:
            print("Error: Source face image is required for CLI mode.")
            print("Usage: python client_ws_lite.py -s <source_face_image> [options]")
            print("   or: python client_ws_lite.py --gui  (for GUI mode)")
            sys.exit(1)
            
        try:
            asyncio.run(main_cli(args))
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)

if __name__ == '__main__':
    main()