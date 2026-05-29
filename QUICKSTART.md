# Quick Start Guide

## 30-Second Setup

### Prerequisites
- Python 3.8+
- Internet connection

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start the Server
```bash
cd backend
python main.py
```

### Step 3: Open in Browser
**Desktop/Laptop:**
```
http://localhost:8000
```

**Mobile/Other Device:**
```
http://YOUR_COMPUTER_IP:8000
```

Find your IP:
- **Windows:** Run `ipconfig` in PowerShell
- **Mac/Linux:** Run `ifconfig` in terminal

---

## Using the App

### 1️⃣ **Login**
- Click "Add New Account"
- Enter phone number with country code (e.g., +919876543210)
- Check Telegram app for OTP code
- Enter code to verify

### 2️⃣ **Download**
- Select your account from dropdown
- Enter channel name (`@channelname`) or link
- Choose media type (Videos, Photos, Documents, Audio, or Everything)
- Click "Start Download"

### 3️⃣ **Monitor**
- Watch real-time progress bar
- See speed and ETA
- View live file count

### 4️⃣ **View Results**
- See summary statistics
- Check downloaded location
- Start another download

---

## Folder Structure

```
backend/
├── main.py           ← FastAPI app
├── downloader.py     ← Download logic
├── config.py         ← Settings
├── sessions/         ← Login tokens (auto-created)
└── downloads/        ← Downloaded files organized by channel
    └── Channel_Name/
        ├── video1.mp4
        ├── photo1.jpg
        └── downloaded_ids.json
```

---

## Troubleshooting

### Issue: "Phone not registered"
**Solution:** Use a phone number with active Telegram account

### Issue: "Can't connect to localhost"
**Solution:** 
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Issue: "Module not found"
**Solution:**
```bash
pip install --upgrade -r requirements.txt
```

### Issue: Slow downloads
**Solution:** Increase workers in `backend/config.py`
```python
MAX_CONCURRENT_WORKERS = 5  # Default is 3
```

---

## Command Reference

### Start with Reload (Development)
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start for Production
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Remote Hosting (Laptop Off)
To run the backend from a remote host and let your phone/tablet connect even when your laptop is off:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then use the remote backend URL in your browser or app shell, for example:

```text
https://your-server-domain-or-ip:8000
```

If the backend is hosted on a public server, make sure port `8000` is accessible or use a reverse proxy.

### Access on Same Network
1. Find your IP: `ipconfig`
2. Share with others: `http://192.168.x.x:8000`

---

## Features at a Glance

✨ **Real-Time Progress**
- Live progress bar
- Speed monitoring (MB/s)
- Time estimate (ETA)

📊 **Detailed Statistics**
- Total files downloaded
- Files by type (videos, photos, docs, audio)
- Total size (GB)
- Download time
- Average speed

🔄 **Smart Deduplication**
- Remembers downloaded files
- Won't re-download same media
- Saves time on re-runs

📱 **Mobile Friendly**
- Works on phone browsers
- Responsive design
- Touch-optimized

🔐 **Multi-Account**
- Login multiple accounts
- Switch between them
- Organized storage per channel

---

## Tips & Tricks

### Organize Downloads
Files are saved to:
```
backend/downloads/Channel_Name/
```

### Resume Downloads
If download interrupts, just download again - it will skip already downloaded files!

### Multiple Channels
Each channel gets its own folder with deduplication tracking.

### Check Download Speed
Watch the speed indicator - if it's slow, wait for server to catch up or reduce workers.

---

## Support Resources

1. **Full Documentation:** See `README.md`
2. **Architecture Details:** See `REFACTORING.md`
3. **Code Comments:** Check `backend/downloader.py` and `backend/main.py`

---

## Common Issues & Solutions

| Problem | Solution |
|---------|----------|
| Browser won't load | Ensure `cd backend` before running `python main.py` |
| OTP not received | Check Telegram app notifications, wait 60 seconds |
| Slow downloads | Increase `MAX_CONCURRENT_WORKERS` in config.py |
| Files not saving | Check write permissions for `backend/downloads/` |
| Can't access from phone | Ensure same WiFi network, use computer's IP address |

---

## Next Steps

- ✅ Refactored code ← You are here
- 🔄 Customize download types (edit `backend/downloader.py`)
- 🚀 Deploy to cloud (AWS, Heroku, DigitalOcean)
- 🗄️ Add database (SQLite, PostgreSQL)
- 📧 Add email notifications

---

**Happy downloading! 🎉**

For detailed help, check the full `README.md`
