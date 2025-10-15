#!/bin/bash
set -e

# -----------------------------
# Configuration
# -----------------------------
PROJECT_DIR="./Deep-Live-Cam-Server"
BRANCH="Server"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="python3"

apt install -y \
    git \
    wget \
    build-essential \
    python3-dev \
    python3-venv \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0
# -----------------------------
# 1. Ensure git, wget, python3, g++ are available
# -----------------------------
command -v git >/dev/null 2>&1 || { echo >&2 "git is required but not found. Install it manually."; exit 1; }
command -v wget >/dev/null 2>&1 || { echo >&2 "wget is required but not found. Install it manually."; exit 1; }
command -v g++ >/dev/null 2>&1 || { echo >&2 "g++ is required but not found. Install it manually."; exit 1; }
command -v $PYTHON_BIN >/dev/null 2>&1 || { echo >&2 "python3 is required but not found. Install it manually."; exit 1; }

# -----------------------------
# 2. Clone repo cleanly
# -----------------------------
if [ -d "$PROJECT_DIR" ]; then
    echo "$PROJECT_DIR already exists, removing..."
    rm -rf "$PROJECT_DIR"
fi

echo "Cloning repository..."
git clone -b $BRANCH https://github.com/bitcoin4cashqc/Deep-Live-Cam-Server.git "$PROJECT_DIR"
cd "$PROJECT_DIR"


# -----------------------------
# 3. Create and activate virtual environment
# -----------------------------
echo "Creating virtual environment..."
$PYTHON_BIN -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# Upgrade pip/setuptools/wheel
pip install --upgrade pip setuptools wheel

# -----------------------------
# 4. Install Python packages
# -----------------------------
echo "Installing Python packages..."

# PyTorch GPU (if available)

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install onnxruntime-gpu

# Other dependencies
pip install opencv-python==4.10.0.84 \
            websockets \
            insightface==0.7.3 \
            "pillow>=11.0.0" \
            psutil \
            opennsfw2 \
            tensorflow

# Git repositories
pip install git+https://github.com/xinntao/BasicSR.git@master
pip install git+https://github.com/TencentARC/GFPGAN.git@master

# -----------------------------
# 5. Download models
# -----------------------------
mkdir -p models
echo "Downloading inswapper_128_fp16.onnx..."
wget -O models/inswapper_128_fp16.onnx "https://huggingface.co/hacksider/deep-live-cam/resolve/main/inswapper_128_fp16.onnx?download=true"

echo "Downloading GFPGANv1.4.pth..."
wget -O models/GFPGANv1.4.pth "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth"

echo "Setup complete!"
echo "Activate your venv with: source $VENV_DIR/bin/activate"
echo "Run the server with: python server_ws.py --headless --execution-provider cuda --execution-threads 4 --server-port 8765"
