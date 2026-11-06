import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.database import init_db
from app.services import git_service, watcher
from app.services.note_service import rebuild_index
from app.api.routes import notes, search, git, tasks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动
    logger.info("MindNet starting...")
    init_db()
    git_service.ensure_repo()
    loop = asyncio.get_running_loop()
    watcher.start_watcher(loop)
    await rebuild_index()
    logger.info("MindNet ready at http://localhost:%s", settings.port)
    yield
    # 关闭
    watcher.stop_watcher()
    logger.info("MindNet stopped.")


app = FastAPI(title="MindNet API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    # 只允许本机前端访问，其他网站不能跨域调用接口改删笔记
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        f"http://localhost:{settings.port}", f"http://127.0.0.1:{settings.port}",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

app.include_router(notes.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(git.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")

# 前端静态文件（构建后）
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=settings.port, reload=False)
