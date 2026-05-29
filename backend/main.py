"""
FastAPI Backend for Telegram Media Downloader
Provides REST API endpoints for authentication and media downloads
"""

import asyncio
import glob
import os
import shutil
import tempfile
import time
import zipfile
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
from backend.downloader import TelegramDownloader, media_label, media_matches, get_media_type
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
session_locks: Dict[str, asyncio.Lock] = {}


def get_session_lock(phone: str) -> asyncio.Lock:
    if phone not in session_locks:
        session_locks[phone] = asyncio.Lock()
    return session_locks[phone]


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
    message_ids: Optional[List[int]] = None


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


def sanitize_filename(name: str) -> str:
    name = name.strip()
    if not name:
        return 'channel'
    safe = ''.join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
    return safe or 'channel'


async def download_worker(
    job_id: str,
    phone: str,
    channel: str,
    choice: str,
    message_ids: Optional[List[int]] = None,
):
    """Background worker for downloads"""
    session_path = os.path.join(SESSIONS_DIR, phone)
    download_root = os.path.join(DOWNLOAD_DIR, phone.lstrip("+"))
    lock = get_session_lock(phone)
    try:
        async with lock:
            print("=" * 50)
            print("WORKER STARTED")
            print("JOB:", job_id)
            print("CHANNEL:", channel)
            print("PHONE:", phone)
            print("=" * 50)

            jobs[job_id]["status"] = "scanning"

            client = TelegramClient(
                session_path,
                API_ID,
                API_HASH,
                connection_retries=10,
                retry_delay=2,
            )

            try:
                await client.connect()

                if not await client.is_user_authorized():
                    raise RuntimeError("Session expired during download")

                downloader = TelegramDownloader(
                    client=client,
                    download_dir=download_root,
                    concurrent_workers=1,
                )

                def progress_update(progress_data: Dict):
                    if job_id in jobs:
                        jobs[job_id]["status"] = "downloading"
                        jobs[job_id]["progress"] = progress_data

                result = await downloader.download_channel(
                    channel=channel,
                    choice=choice,
                    message_ids=message_ids,
                    progress_callback=progress_update,
                )

                jobs[job_id]["status"] = "completed" if result.get("success") else "failed"
                jobs[job_id]["result"] = result
                jobs[job_id]["stats"] = result.get("stats", {})

            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass

    except Exception as e:
        import traceback

        print("=" * 50)
        print("DOWNLOAD ERROR")
        traceback.print_exc()
        print("=" * 50)

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


@app.get("/api/history/{phone}")
async def get_history(phone: str):
    if not phone.startswith("+"):
        phone = "+" + phone

    user_folder = os.path.join(
        DOWNLOAD_DIR,
        phone.lstrip("+")
    )

    if not os.path.exists(user_folder):
        return {
            "success": True,
            "channels": []
        }

    channels = []

    for folder in os.listdir(user_folder):

        folder_path = os.path.join(
            user_folder,
            folder
        )

        if not os.path.isdir(folder_path):
            continue

        file_count = 0
        total_size = 0

        for root, _, files in os.walk(folder_path):
            for file in files:

                if file == "downloaded_ids.json":
                    continue

                path = os.path.join(
                    root,
                    file
                )

                file_count += 1
                total_size += os.path.getsize(path)

        channels.append({
            "name": folder,
            "files": file_count,
            "size_mb": round(
                total_size / 1024 / 1024,
                2
            )
        })

    return {
        "success": True,
        "channels": channels
    }


@app.get("/api/channel/media")
async def get_channel_media(phone: str, channel: str, download_type: str = "5"):
    """List matching media items in a channel for selection."""
    if not phone.startswith("+"):
        phone = "+" + phone

    session_path = os.path.join(SESSIONS_DIR, phone)
    if not os.path.exists(session_path + ".session"):
        raise HTTPException(
            status_code=401,
            detail="Account not logged in"
        )

    lock = get_session_lock(phone)
    async with lock:
        client = TelegramClient(
            session_path,
            API_ID,
            API_HASH,
            connection_retries=10,
            retry_delay=2,
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise HTTPException(
                    status_code=401,
                    detail="Session expired. Please login again."
                )

            entity = await client.get_entity(channel)
            items = []
            count = 0
            async for message in client.iter_messages(entity):
                if media_matches(message, download_type):
                    if count >= 500:
                        break
                    media_type = get_media_type(message)
                    size = 0
                    if getattr(message, 'file', None):
                        size = message.file.size or 0
                    items.append({
                        'id': message.id,
                        'date': message.date.isoformat() if getattr(message, 'date', None) else None,
                        'type': media_type,
                        'size': size,
                        'caption': (getattr(message, 'message', '') or '')[:200],
                    })
                    count += 1

            return {
                'success': True,
                'channel': channel,
                'download_type': download_type,
                'items': items,
                'total_items': len(items),
            }

        finally:
            try:
                await client.disconnect()
            except Exception:
                pass


@app.post("/api/login")
async def login(request: LoginRequest):
    from telethon.errors import AuthRestartError

    phone = request.phone.strip()

    if not phone.startswith("+"):
        phone = "+" + phone

    # Prevent multiple OTP requests - clean up old session
    if phone in clients:
        try:
            await clients[phone].disconnect()
        except Exception:
            pass
        clients.pop(phone, None)

    session_path = os.path.join(SESSIONS_DIR, phone)
    lock = get_session_lock(phone)

    try:
        async with lock:
            client = TelegramClient(
                session_path,
                API_ID,
                API_HASH,
                connection_retries=10,
                retry_delay=2,
            )

            try:
                if not client.is_connected():
                    await client.connect()

                await client.send_code_request(phone)

            except AuthRestartError:
                print("Telegram requested auth restart")

                await client.disconnect()

                client = TelegramClient(
                    session_path,
                    API_ID,
                    API_HASH,
                    connection_retries=10,
                    retry_delay=2,
                )

                await client.connect()
                await asyncio.sleep(2)
                await client.send_code_request(phone)

            clients[phone] = client

        return {
            "success": True,
            "phone": phone,
            "message": "OTP sent successfully"
        }

    except Exception as e:
        import traceback

        print("\n" + "=" * 60)
        print("LOGIN ERROR")
        print("TYPE:", type(e).__name__)
        print("ERROR:", str(e))
        traceback.print_exc()
        print("=" * 60 + "\n")

        raise HTTPException(
            status_code=400,
            detail=f"{type(e).__name__}: {str(e)}"
        )

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
    lock = get_session_lock(phone)

    try:
        async with lock:
            try:
                if request.password:
                    await client.sign_in(phone=phone, code=request.code, password=request.password)
                else:
                    await client.sign_in(phone=phone, code=request.code)
            except SessionPasswordNeededError:
                return {
                    "success": False,
                    "requires_password": True,
                    "phone": phone,
                    "message": "2FA password required"
                }

            if await client.is_user_authorized():
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
        try:
            await client.sign_in(password=request.password)

            if await client.is_user_authorized():
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
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/download/zip")
async def download_videos_zip(phone: str, channel: str, background_tasks: BackgroundTasks):
    """Create a ZIP from the already-downloaded files for this account/channel."""
    if not phone.startswith("+"):
        phone = "+" + phone

    session_path = os.path.join(SESSIONS_DIR, phone)
    download_root = os.path.join(DOWNLOAD_DIR, phone.lstrip("+"))
    if not os.path.exists(session_path + ".session"):
        raise HTTPException(
            status_code=401,
            detail="Account not logged in"
        )

    lock = get_session_lock(phone)
    async with lock:
        client = TelegramClient(
            session_path,
            API_ID,
            API_HASH,
            connection_retries=10,
            retry_delay=2,
        )

        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise HTTPException(
                    status_code=401,
                    detail="Session expired. Please login again."
                )

            entity = await client.get_entity(channel)
            channel_name = sanitize_filename(getattr(entity, "title", "channel"))
            channel_folder = os.path.join(download_root, channel_name)
            if not os.path.exists(channel_folder):
                raise HTTPException(
                    status_code=404,
                    detail="No downloaded files found for this channel."
                )

            temp_dir = tempfile.mkdtemp(prefix=f"zip_{channel_name}_", dir=download_root)
            zip_filename = f"{channel_name}_videos_{int(time.time())}.zip"
            zip_path = os.path.join(download_root, zip_filename)

            file_count = 0
            for root, _, files in os.walk(channel_folder):
                for file_name in files:
                    source_path = os.path.join(root, file_name)
                    if source_path.endswith("downloaded_ids.json"):
                        continue
                    relative_path = os.path.relpath(source_path, channel_folder)
                    target_path = os.path.join(temp_dir, relative_path)
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(source_path, target_path)
                    file_count += 1

            if file_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail="No downloaded media files found for this channel."
                )

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for root, _, files in os.walk(temp_dir):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        archive_name = os.path.relpath(file_path, temp_dir)
                        zip_file.write(file_path, archive_name)

            background_tasks.add_task(shutil.rmtree, temp_dir, True)
            background_tasks.add_task(os.remove, zip_path)

            return FileResponse(
                zip_path,
                filename=zip_filename,
                media_type="application/zip",
                background=background_tasks,
            )

        finally:
            try:
                await client.disconnect()
            except Exception:
                pass


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

    lock = get_session_lock(phone)

    try:
        async with lock:
            client = TelegramClient(
                session_path,
                API_ID,
                API_HASH,
                connection_retries=10,
                retry_delay=2,
            )
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    jobs[job_id]["status"] = "failed"
                    jobs[job_id]["error"] = "Session expired"
                    raise HTTPException(
                        status_code=401,
                        detail="Session expired. Please login again."
                    )
            finally:
                try:
                    await client.disconnect()
                except Exception:
                    pass

        background_tasks.add_task(
            download_worker,
            job_id,
            phone,
            request.channel,
            request.download_type,
            request.message_ids,
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

    session_glob = os.path.join(SESSIONS_DIR, phone + ".session*")
    for path in glob.glob(session_glob):
        try:
            os.remove(path)
        except Exception:
            pass

    return {
        "success": True,
        "phone": phone,
        "message": "Logged out successfully"
    }

@app.get("/debug/storage")
def debug_storage():
    result = {
        "cwd": os.getcwd(),
        "backend_exists": os.path.exists("backend"),
        "downloads_exists": os.path.exists("backend/downloads"),
        "download_dir_config": DOWNLOAD_DIR,
    }

    if os.path.exists("backend/downloads"):
        try:
            result["downloads"] = os.listdir("backend/downloads")
        except Exception as e:
            result["downloads_error"] = str(e)

    # also check configured absolute download dir
    try:
        if os.path.exists(DOWNLOAD_DIR):
            result["configured_downloads"] = os.listdir(DOWNLOAD_DIR)
    except Exception as e:
        result["configured_downloads_error"] = str(e)

    return result


@app.get("/debug/tree")
def debug_tree():
    import os

    matches = []

    for root, dirs, files in os.walk("."):
        if "download" in root.lower():
            matches.append(root)

    return {
        "cwd": os.getcwd(),
        "matches": matches
    }


@app.get("/files")
def list_files():
    files = []

    for root, dirs, filenames in os.walk("/app/backend/downloads"):
        for filename in filenames:
            files.append(os.path.join(root, filename))

    return files


@app.get("/download-file")
def download_file(filename: str):
    path = os.path.join("/app/backend/downloads", filename)

    if os.path.exists(path):
        return FileResponse(path)

    return {"error": "File not found"}