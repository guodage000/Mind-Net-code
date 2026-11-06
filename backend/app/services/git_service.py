import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_pending_task: Optional[asyncio.Task] = None
_last_sync: Optional[str] = None
_last_error: Optional[str] = None


def _git_repo():
    try:
        import git
        return git.Repo(settings.vault_path)
    except Exception:
        return None


def ensure_repo() -> bool:
    """确保 vault 目录是 Git 仓库，不是则初始化"""
    import git
    vault = settings.vault_path
    vault.mkdir(parents=True, exist_ok=True)
    try:
        git.Repo(vault)
        return True
    except git.InvalidGitRepositoryError:
        git.Repo.init(vault)
        logger.info("Initialized new git repo at %s", vault)
        return True
    except Exception as e:
        logger.error("Git init failed: %s", e)
        return False


async def schedule_sync():
    """触发防抖同步：在 git_debounce_seconds 秒内无新触发时执行提交"""
    global _pending_task
    if _pending_task and not _pending_task.done():
        _pending_task.cancel()
    _pending_task = asyncio.create_task(_delayed_sync())


async def _delayed_sync():
    global _last_sync, _last_error
    try:
        await asyncio.sleep(settings.git_debounce_seconds)
        await _do_sync()
    except asyncio.CancelledError:
        pass  # 被新的编辑打断，正常
    except Exception as e:
        _last_error = str(e)
        logger.error("Git sync error: %s", e)


async def _do_sync():
    global _last_sync, _last_error
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _sync_blocking)


def _sync_blocking():
    global _last_sync, _last_error
    import git
    try:
        repo = _git_repo()
        if not repo:
            return
        repo.git.add(A=True)
        if not repo.is_dirty(index=True, untracked_files=True):
            return  # 没有变化，跳过
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        repo.index.commit(f"auto: {ts}")
        _last_sync = datetime.now(timezone.utc).isoformat()
        _last_error = None
        logger.info("Committed changes at %s", _last_sync)

        if settings.git_remote:
            origin = repo.remote(name="origin")
            origin.push(refspec=f"HEAD:{settings.git_branch}")
            logger.info("Pushed to %s/%s", settings.git_remote, settings.git_branch)
    except Exception as e:
        _last_error = str(e)
        logger.error("Git sync blocking error: %s", e)


def get_status() -> dict:
    import git
    try:
        repo = _git_repo()
        if not repo:
            return {"enabled": False, "remote": "", "branch": "", "pending_changes": 0,
                    "last_sync": None, "error": "Not a git repo"}
        changed = len(repo.index.diff(None)) + len(repo.untracked_files)
        return {
            "enabled": True,
            "remote": settings.git_remote,
            "branch": settings.git_branch,
            "pending_changes": changed,
            "last_sync": _last_sync,
            "error": _last_error,
        }
    except Exception as e:
        return {"enabled": False, "remote": "", "branch": "", "pending_changes": 0,
                "last_sync": None, "error": str(e)}
