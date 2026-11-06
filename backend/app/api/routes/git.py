from fastapi import APIRouter
from app.services import git_service
from app.models.schemas import GitStatus

router = APIRouter(prefix="/git", tags=["git"])


@router.get("/status", response_model=GitStatus)
def git_status():
    return git_service.get_status()


@router.post("/sync")
async def manual_sync():
    await git_service._do_sync()
    return {"ok": True}
