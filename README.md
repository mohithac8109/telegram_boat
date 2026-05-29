# Telegram Media Manager

A modern web application for downloading videos, photos, documents, and audio from Telegram channels with real-time progress tracking, statistics, and deduplication.

## Features

✨ **Core Features**
- 📺 Download videos, photos, documents, and audio
- 🎯 Download specific media types from channels
- 📊 Real-time progress bar with speed and ETA
- 💾 Automatic deduplication (skip already downloaded files)
- 🔄 Concurrent downloads (3 parallel workers)
- 📈 Detailed statistics dashboard
- 🌐 Web-based UI (mobile-friendly)
- 🔐 Multi-account support

**Statistics Tracked**
- Total files downloaded
- Files by type (videos, photos, documents, audio)
- Total size in GB
- Download time
- Average speed (MB/s)

## Project Structure

```
telegram_boat/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── downloader.py           # Download service
│   ├── config.py               # Configuration
│   ├── sessions/               # Telegram session files
│   └── downloads/              # Downloaded media
├── frontend/
│   ├── index.html              # Dashboard UI
│   ├── app.js                  # Client-side logic
│   └── style.css               # Responsive styling
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Step 1: Clone or Setup Project

```bash
cd telegram_boat
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Telegram API

Edit `backend/config.py` and add your API credentials (if not already set):

```python
API_ID = YOUR_API_ID
API_HASH = "YOUR_API_HASH"
```

Get your credentials from: https://my.telegram.org/apps

## Running the Application

### Method 1: Direct Run (Development)

```bash
cd backend
python main.py
```

Then open your browser: **http://localhost:8000**

### Method 2: Using Uvicorn with Reload

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Method 3: Production Run

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Remote Hosting (Phone/Tablet Access)

To keep the backend running when your laptop is off, deploy the backend on a remote server or VPS and run:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then point your phone/tablet browser or Android shell app to the remote host URL, for example:

```text
https://your-server-domain-or-ip:8000
```

If your remote host supports HTTPS, use that URL. If you use a public IP, ensure port `8000` is open or use a reverse proxy such as Nginx.

### Free / low-cost hosting options
- Railway (free tier for small apps)
- Fly.io (free tier with persistent service)
- Koyeb (free tier for web services)
- PythonAnywhere (free web app with restrictions)
- Any VPS or cloud VM with Python support

> Note: A truly remote backend must stay online to keep downloads working. If the backend is on a remote host, your laptop can be off and the mobile front end will still work.

## Usage

### 1. **Login to Telegram**
   - Click "Add New Account"
   - Enter your phone number (with country code)
   - Enter the OTP from your Telegram app

### 2. **Select Account & Channel**
   - Choose an account from the dropdown
   - Enter channel name (`@channelname`) or link
   - Select media type to download

### 3. **Monitor Download**
   - View real-time progress bar
   - Track speed and ETA
   - See live statistics

### 4. **View Results**
   - Summary dashboard with stats
   - Total files and size downloaded
   - Download location

## API Endpoints

### Authentication
- `POST /api/login` - Request OTP
- `POST /api/login/verify` - Verify OTP
- `POST /api/logout` - Logout account

### Download Management
- `POST /api/download` - Start download job
- `GET /api/download/status/{job_id}` - Check job progress

### Account Management
- `GET /api/accounts` - List saved accounts

### Health Check
- `GET /api/health` - Server status

## Downloading from Different Devices

Once running, access from:

**Laptop (same machine):**
```
http://localhost:8000
```

**Other devices (same network):**
```
http://192.168.1.100:8000
(Replace with your machine's local IP)
```

**Find your IP:**
```bash
# Windows
ipconfig

# macOS/Linux
ifconfig
```

## Advanced Configuration

### Customize Download Types

Edit `backend/downloader.py`:
```python
DOWNLOAD_TYPE_VIDEO = "1"
DOWNLOAD_TYPE_PHOTO = "2"
DOWNLOAD_TYPE_DOCUMENT = "3"
DOWNLOAD_TYPE_AUDIO = "4"
DOWNLOAD_TYPE_EVERYTHING = "5"
```

### Change Concurrent Workers

Edit `backend/config.py`:
```python
MAX_CONCURRENT_WORKERS = 3  # Increase for faster downloads
```

### Session & Download Locations

```
backend/
├── sessions/          # Telegram session files
│   └── +91XXXXX.session
└── downloads/         # Downloaded media
    └── Channel_Name/
        ├── video1.mp4
        ├── photo1.jpg
        └── downloaded_ids.json
```

## Troubleshooting

### "Phone not registered" Error
- Ensure you're using the correct phone number with country code
- The phone must have a Telegram account

### "Session expired" Error
- Clear the session file and login again
- Session files in `backend/sessions/`

### 2FA (Two-Factor Auth) Required
- Currently, 2FA is not fully supported
- Disable 2FA temporarily or add password support

### Slow Downloads
- Increase `MAX_CONCURRENT_WORKERS` to 5-10
- Check your internet connection
- Telegram may rate-limit very fast downloads

### Deduplication Not Working
- Ensure `downloaded_ids.json` exists in the channel folder
- File stores already downloaded message IDs

## File Storage

Downloaded files are organized by channel:

```
downloads/
├── Tech_Channel/
│   ├── video_1.mp4
│   ├── photo_2.jpg
│   └── downloaded_ids.json
└── News_Channel/
    ├── document_1.pdf
    ├── audio_2.m4a
    └── downloaded_ids.json
```

The `downloaded_ids.json` tracks downloaded message IDs to prevent re-downloading.

## Performance Tips

1. **Use Concurrent Downloads**: Keep workers at 3-5 for stability
2. **Channel Size**: Large channels (10K+ files) may take time to scan
3. **Network**: Fast connection improves download speed
4. **Storage**: Ensure enough disk space before downloading
5. **API Rate Limits**: Telegram limits concurrent connections; don't use more than 10 workers

## Security Notes

- ⚠️ Session files store authentication tokens
- Keep `backend/sessions/` folder secure
- Don't share session files
- Run behind HTTPS in production
- Use strong Telegram 2FA (when supported)

## Limitations

- 2FA not supported (workaround: disable temporarily)
- Large files may timeout (1GB+)
- Channel access required (must join channel first)
- Respects Telegram's rate limits

## Technology Stack

**Backend:**
- FastAPI - Modern Python web framework
- Telethon - Telegram client library
- Pydantic - Data validation

**Frontend:**
- HTML5 - Structure
- CSS3 - Responsive design
- JavaScript (Vanilla) - Interactivity

**Deployment:**
- Uvicorn - ASGI server
- Python 3.8+

## Development

### Directory Structure
```
backend/
├── main.py         - FastAPI app & endpoints
├── downloader.py   - Download logic
├── config.py       - Settings
├── sessions/       - Auth tokens
└── downloads/      - Media

frontend/
├── index.html      - UI structure
├── app.js          - Logic & API calls
└── style.css       - Responsive styles
```

### Adding Features

1. **New Download Type**: Modify `downloader.py` `media_matches()`
2. **New Endpoint**: Add to `main.py`
3. **UI Changes**: Edit `frontend/index.html` and `app.js`
4. **Styling**: Update `frontend/style.css`

## License

This project is provided as-is for personal use.

## Support

For issues or questions:
1. Check Telegram's official documentation
2. Review error messages in browser console
3. Check server logs in terminal

## Disclaimer

This tool is for personal use only. Ensure you have permission to download media from channels. Respect copyright and Telegram's terms of service.

---

**Made with ❤️ | Telegram Media Manager v1.0**
