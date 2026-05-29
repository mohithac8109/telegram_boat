"""
FastAPI Backend for Telegram Media Downloader
Provides REST API endpoints for authentication and media downloads
"""

import os
import uuid
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from backend.config import API_ID, API_HASH, SESSIONS_DIR, DOWNLOAD_DIR
from backend.config import API_ID, API_HASH, SESSIONS_DIR, DOWNLOAD_DIR

app = FastAPI(title="Telegram Media Downloader API", version="1.0.0")

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Static file serving for PWA assets
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job tracking
jobs: Dict[str, Dict] = {}
clients: Dict[str, TelegramClient] = {}


# Models
class LoginRequest(BaseModel):
    phone: str


class LoginVerifyRequest(BaseModel):
    phone: str
    code: str
    password: Optional[str] = None


class DownloadRequest(BaseModel):
    phone: str
    channel: str
    download_type: str  # "1", "2", "3", "4", "5"


# Utility Functions
def get_saved_accounts() -> List[str]:
    """Get list of saved account phone numbers"""
    accounts = []
    if os.path.exists(SESSIONS_DIR):
        for file in os.listdir(SESSIONS_DIR):
            if file.endswith(".session"):
                phone = file.replace(".session", "")
                accounts.append(phone)
    return sorted(accounts)


async def download_worker(
    job_id: str, client: TelegramClient, channel: str, choice: str
):
    """Background worker for downloads"""
    try:
        jobs[job_id]["status"] = "scanning"

        downloader = TelegramDownloader(
            client=client,
            download_dir=DOWNLOAD_DIR,
            concurrent_workers=3,
        )

        def progress_update(progress_data: Dict):
            if job_id in jobs:
                jobs[job_id]["progress"] = progress_data

        result = await downloader.download_channel(
            channel=channel,
            choice=choice,
            progress_callback=progress_update,
        )

        jobs[job_id]["status"] = "completed" if result.get("success") else "failed"
        jobs[job_id]["result"] = result
        jobs[job_id]["stats"] = result.get("stats", {})

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)


# API Endpoints
@app.get("/")
async def root():
    """Serve frontend"""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/manifest.json")
async def manifest():
    return FileResponse(FRONTEND_DIR / "manifest.json")


@app.get("/sw.js")
async def service_worker():
    return FileResponse(FRONTEND_DIR / "sw.js")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/accounts")
async def get_accounts():
    """Get list of saved accounts"""
    accounts = get_saved_accounts()
    return {
        "accounts": accounts,
        "count": len(accounts),
    }


@app.post("/api/login")
async def login(request: LoginRequest):
    """Request OTP for Telegram login"""
    phone = request.phone.strip()

    if not phone.startswith("+"):
        phone = "+" + phone

    session_path = os.path.join(SESSIONS_DIR, phone)

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        (phone_registered, account_exists) = (
            await client.is_phone_registered()
        )

        if not phone_registered:
            await client.disconnect()
            raise HTTPException(
                status_code=400,
                detail="Phone number not registered on Telegram"
            )

        sent_code = await client.send_code_request(phone)
        clients[phone] = client

        return {
            "success": True,
            "phone": phone,
            "message": "OTP sent to Telegram app",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/login/verify")
async def verify_login(request: LoginVerifyRequest):
    """Verify OTP and complete login"""
    phone = request.phone.strip()

    if not phone.startswith("+"):
        phone = "+" + phone

    if phone not in clients:
        raise HTTPException(
            status_code=400,
            detail="Phone not found. Request OTP first."
        )

    client = clients[phone]

    try:
        await client.sign_in(phone=phone, code=request.code)

        if client.is_user_authorized():
            me = await client.get_me()
            await client.disconnect()
            clients.pop(phone, None)

            return {
                "success": True,
                "phone": phone,
                "user": {
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "username": me.username,
                },
                "message": "Login successful"
            }

        raise HTTPException(
            status_code=400,
            detail="Login failed"
        )

    except SessionPasswordNeededError:
        return {
            "success": False,
            "requires_password": True,
            "phone": phone,
            "message": "2FA password required"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
async def start_download(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Start a media download job"""
    phone = request.phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone

    if request.download_type not in {"1", "2", "3", "4", "5"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid download_type. Use 1-5."
        )

    session_path = os.path.join(SESSIONS_DIR, phone)

    if not os.path.exists(session_path + ".session"):
        raise HTTPException(
            status_code=401,
            detail="Account not logged in"
        )

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "phone": phone,
        "channel": request.channel,
        "download_type": request.download_type,
        "progress": None,
        "stats": None,
    }

    try:
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = "Session expired"
            raise HTTPException(
                status_code=401,
                detail="Session expired. Please login again."
            )

        background_tasks.add_task(
            download_worker,
            job_id,
            client,
            request.channel,
            request.download_type,
        )

        return {
            "success": True,
            "job_id": job_id,
            "status": jobs[job_id]["status"],
            "message": f"Download started for {media_label(request.download_type)}"
        }

    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/download/status/{job_id}")
async def get_download_status(job_id: str):
    """Get status of a download job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress"),
        "stats": job.get("stats"),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
    }


@app.post("/api/logout")
async def logout(request: LoginRequest):
    """Logout and remove session"""
    phone = request.phone.strip()

    if not phone.startswith("+"):
        phone = "+" + phone

    session_path = os.path.join(SESSIONS_DIR, phone + ".session")

    if os.path.exists(session_path):
        os.remove(session_path)

    return {
        "success": True,
        "phone": phone,
        "message": "Logged out successfully"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
