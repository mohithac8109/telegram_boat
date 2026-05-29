"""
Telegram Media Downloader Service
Handles all download operations, progress tracking, and statistics
"""

import asyncio
import json
import os
import time
from typing import Dict, Optional, Callable
from telethon import TelegramClient
from telethon.errors import ChannelInvalidError

DOWNLOAD_TYPE_VIDEO = "1"
DOWNLOAD_TYPE_PHOTO = "2"
DOWNLOAD_TYPE_DOCUMENT = "3"
DOWNLOAD_TYPE_AUDIO = "4"
DOWNLOAD_TYPE_EVERYTHING = "5"


def load_downloaded_ids(channel_folder: str) -> set:
    """Load previously downloaded message IDs from JSON file"""
    record_file = os.path.join(channel_folder, "downloaded_ids.json")
    if os.path.exists(record_file):
        with open(record_file, "r", encoding="utf-8") as f:
            try:
                return set(json.load(f))
            except (ValueError, TypeError):
                return set()
    return set()


def save_downloaded_ids(channel_folder: str, ids: set) -> None:
    """Save downloaded message IDs to JSON file"""
    record_file = os.path.join(channel_folder, "downloaded_ids.json")
    with open(record_file, "w", encoding="utf-8") as f:
        json.dump(sorted(ids), f)


def media_matches(message, choice: str) -> bool:
    """Check if message matches the selected download type"""
    if choice == DOWNLOAD_TYPE_VIDEO:
        return bool(message.video)
    if choice == DOWNLOAD_TYPE_PHOTO:
        return bool(message.photo)
    if choice == DOWNLOAD_TYPE_DOCUMENT:
        return bool(message.document and not message.video)
    if choice == DOWNLOAD_TYPE_AUDIO:
        return bool(message.audio)
    if choice == DOWNLOAD_TYPE_EVERYTHING:
        return bool(
            message.video
            or message.photo
            or message.document
            or message.audio
        )
    return False


def get_media_type(message) -> Optional[str]:
    """Return the type of media in the message"""
    if message.video:
        return "video"
    if message.photo:
        return "photo"
    if message.audio:
        return "audio"
    if message.document:
        return "document"
    return None


def media_label(choice: str) -> str:
    """Get friendly label for download type"""
    labels = {
        DOWNLOAD_TYPE_VIDEO: "videos",
        DOWNLOAD_TYPE_PHOTO: "photos",
        DOWNLOAD_TYPE_DOCUMENT: "documents",
        DOWNLOAD_TYPE_AUDIO: "audios",
        DOWNLOAD_TYPE_EVERYTHING: "files",
    }
    return labels.get(choice, "files")


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{int(secs):02d}"


def format_size(bytes_size: float) -> str:
    """Format bytes to human-readable size"""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.2f} TB"


class DownloadProgressTracker:
    """Track download progress and statistics"""

    def __init__(self, on_progress: Optional[Callable] = None):
        self.on_progress = on_progress
        self.start_time = time.monotonic()
        self.last_update = self.start_time

    def callback(self, current: int, total: int) -> None:
        """Progress callback for Telethon"""
        now = time.monotonic()
        if now - self.last_update < 0.2:  # Update max 5 times per second
            return

        self.last_update = now
        elapsed = max(now - self.start_time, 0.001)
        percent = (current * 100 / total) if total else 0
        speed_mbps = current / elapsed / 1024 / 1024
        remaining_bytes = max(total - current, 0)
        eta_seconds = remaining_bytes / (current / elapsed) if current else 0

        progress_data = {
            "percent": percent,
            "current_mb": current / 1024 / 1024,
            "total_mb": total / 1024 / 1024,
            "speed_mbps": speed_mbps,
            "eta": format_time(eta_seconds),
        }

        if self.on_progress:
            self.on_progress(progress_data)


class TelegramDownloader:
    """Main downloader service"""

    def __init__(
        self,
        client: TelegramClient,
        download_dir: str,
        concurrent_workers: int = 3,
    ):
        self.client = client
        self.download_dir = download_dir
        self.concurrent_workers = concurrent_workers
        self.current_job: Optional[Dict] = None

    async def count_media(self, entity, choice: str) -> int:
        """Count total media items matching the choice"""
        count = 0
        async for message in self.client.iter_messages(entity):
            if media_matches(message, choice):
                count += 1
        return count

    async def download_message(
        self,
        message,
        channel_folder: str,
        item_index: int,
        total_items: int,
        downloaded_ids: set,
        stats: Dict,
        id_lock: asyncio.Lock,
        progress_callback: Optional[Callable] = None,
    ) -> bool:
        """Download a single message"""
        file_size = 0
        if getattr(message, "file", None):
            file_size = message.file.size or 0

        tracker = DownloadProgressTracker(progress_callback)

        try:
            await self.client.download_media(
                message,
                file=channel_folder,
                progress_callback=tracker.callback,
            )

            async with id_lock:
                downloaded_ids.add(message.id)
                save_downloaded_ids(channel_folder, downloaded_ids)

                media_type = get_media_type(message)
                if media_type == "video":
                    stats["video_count"] += 1
                elif media_type == "photo":
                    stats["photo_count"] += 1
                elif media_type == "audio":
                    stats["audio_count"] += 1
                elif media_type == "document":
                    stats["document_count"] += 1

                stats["total_size"] += file_size
                stats["downloaded_count"] += 1

            return True
        except Exception as e:
            print(f"Error downloading message {message.id}: {e}")
            return False

    async def download_channel(
        self,
        channel: str,
        choice: str,
        progress_callback: Optional[Callable] = None,
    ) -> Dict:
        """
        Download media from a channel

        Returns:
            dict: Statistics and results
        """
        try:
            entity = await self.client.get_entity(channel)
        except ChannelInvalidError:
            return {"error": "Invalid channel or not authorized"}

        channel_name = getattr(entity, "title", "Unknown_Channel")
        channel_name = "".join(
            c for c in channel_name
            if c.isalnum() or c in (" ", "_", "-")
        )

        channel_folder = os.path.join(self.download_dir, channel_name)
        os.makedirs(channel_folder, exist_ok=True)

        downloaded_ids = load_downloaded_ids(channel_folder)
        label = media_label(choice)

        start_time = time.time()

        stats = {
            "channel_name": channel_name,
            "channel_folder": channel_folder,
            "download_type": label,
            "total_size": 0,
            "video_count": 0,
            "photo_count": 0,
            "document_count": 0,
            "audio_count": 0,
            "downloaded_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
        }

        total_matches = await self.count_media(entity, choice)
        if total_matches == 0:
            return {
                "success": False,
                "message": f"No {label} found in channel",
                "stats": stats,
            }

        queue: asyncio.Queue = asyncio.Queue(maxsize=20)
        id_lock = asyncio.Lock()

        async def worker(worker_id: int) -> None:
            while True:
                item = await queue.get()
                if item is None:
                    queue.task_done()
                    break

                message, item_index = item

                if message.id in downloaded_ids:
                    stats["skipped_count"] += 1
                    queue.task_done()
                    continue

                success = await self.download_message(
                    message,
                    channel_folder,
                    item_index,
                    total_matches,
                    downloaded_ids,
                    stats,
                    id_lock,
                    progress_callback,
                )

                if not success:
                    stats["failed_count"] += 1

                queue.task_done()

        workers = [
            asyncio.create_task(worker(i))
            for i in range(self.concurrent_workers)
        ]

        item_index = 0
        async for message in self.client.iter_messages(entity):
            if media_matches(message, choice):
                item_index += 1
                await queue.put((message, item_index))

        for _ in workers:
            await queue.put(None)

        await queue.join()
        await asyncio.gather(*workers)

        end_time = time.time()
        elapsed_time = end_time - start_time

        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)

        avg_speed = 0.0
        if elapsed_time > 0:
            avg_speed = stats["total_size"] / elapsed_time / 1024 / 1024

        stats.update({
            "elapsed_time": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "elapsed_seconds": elapsed_time,
            "avg_speed_mbps": avg_speed,
            "total_size_gb": stats["total_size"] / 1024 / 1024 / 1024,
            "total_items_found": total_matches,
        })

        return {
            "success": True,
            "message": "Download completed",
            "stats": stats,
        }
