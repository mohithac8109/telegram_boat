"""Backend Configuration"""

import os

# Telegram API Credentials
API_ID = 37097586
API_HASH = "c045adeff08f1d102088c9df1ed9caac"

# Directory Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

# Ensure directories exist
os.makedirs(SESSIONS_DIR, exist_ok=True)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Server Configuration
HOST = "0.0.0.0"
PORT = 8000
DEBUG = True

# Download Configuration
MAX_CONCURRENT_WORKERS = 3
QUEUE_MAX_SIZE = 20