import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from app.core.config import settings
from app.services import git_service

logger = logging.getLogger(__name__)
_loop: asyncio.AbstractEventLoop = None


class VaultEventHandler(FileSystemEventHandler):
    def on_any_event(self, event: FileSystemEvent):
        if event.is_directory:
            return
        src = str(event.src_path)
        if not src.endswith(".md"):
            return
        if _loop and _loop.is_running():
            asyncio.run_coroutine_threadsafe(git_service.schedule_sync(), _loop)


_observer: Observer = None


def start_watcher(loop: asyncio.AbstractEventLoop):
    global _observer, _loop
    _loop = loop
    settings.vault_path.mkdir(parents=True, exist_ok=True)
    _observer = Observer()
    _observer.schedule(VaultEventHandler(), str(settings.vault_path), recursive=True)
    _observer.start()
    logger.info("File watcher started on %s", settings.vault_path)


def stop_watcher():
    if _observer:
        _observer.stop()
        _observer.join()
