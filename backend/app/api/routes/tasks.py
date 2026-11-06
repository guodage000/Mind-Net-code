import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.models.schemas import Note, NoteCreate, NoteUpdate
from app.models.tasks import TaskItem, TaskSummary, ImportRequest, MoveTask
from app.services import note_service

router = APIRouter(tags=["tasks"])

STATUSES = ("todo", "in_progress", "done", "blocked")
MD_SUFFIXES = {".md", ".markdown", ".mdown", ".mkd"}


# ─── 任务状态 ────────────────────────────────────────────────────────────────
class StatusUpdate(BaseModel):
    status: str


@router.get("/tasks", response_model=TaskSummary)
def list_tasks():
    """所有任务，按状态分组。普通笔记里如果勾选了一半以上也会算进任务列表。"""
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, title, status, priority, deadline, tags, note_type, content, updated_at, parent_id "
            "FROM notes WHERE note_type = 'task' ORDER BY updated_at DESC"
        ).fetchall()
    finally:
        conn.close()

    # 先按 parent_id 分组，找出每个任务的子任务
    children_map = {}
    for r in rows:
        if r["parent_id"]:
            children_map.setdefault(r["parent_id"], []).append(r["id"])

    tasks: List[TaskItem] = []
    counts = {s: 0 for s in STATUSES}
    for r in rows:
        total, finished = note_service.checklist_stats(r["content"] or "")
        has_boxes = total > 0
        status = r["status"]
        if not status:
            if not has_boxes:
                status = "todo"
            else:
                status = "done" if finished == total else ("in_progress" if finished else "todo")

        # 汇总正文里的截止日期/时间（取最早的）
        content = r["content"] or ""
        dates = re.findall(r"\[(\d{4}-\d{2}-\d{2})\]", content)
        times = re.findall(r"\[(\d{1,2}:\d{2})\]", content)
        deadline = r["deadline"] or (min(dates) if dates else None)
        time = min(times) if times else None
        # 有缩进的任务行算子任务（正文清单）
        has_subtasks = bool(re.search(r"^\s+[-*+]\s+\[[ xX/]\]", content, re.MULTILINE))
        # 独立文件的子任务（通过 parent_id 关联）
        subtask_ids = children_map.get(r["id"], [])

        item = TaskItem(
            id=r["id"], title=r["title"], status=status,
            priority=r["priority"], deadline=deadline, time=time,
            tags=json.loads(r["tags"]) if r["tags"] else [],
            updated_at=r["updated_at"], total=total, finished=finished,
            hasSubtasks=has_subtasks or len(subtask_ids) > 0,
            subtaskIds=subtask_ids,
            parentId=r["parent_id"],
        )
        tasks.append(item)
        counts[status] = counts.get(status, 0) + 1
    return TaskSummary(tasks=tasks, counts=counts)


@router.patch("/tasks/{note_id:path}/status", response_model=Note)
async def set_status(note_id: str, body: StatusUpdate):
    if body.status not in STATUSES:
        raise HTTPException(400, f"状态只能是：{' / '.join(STATUSES)}")
    note = await note_service.update_note(note_id, NoteUpdate(status=body.status))
    if not note:
        raise HTTPException(404, f"笔记不存在：{note_id}")
    return note


@router.patch("/tasks/{note_id:path}/move", response_model=Note)
async def move_task(note_id: str, body: MoveTask):
    """移动任务到另一个父任务下，或变成顶层任务。孙任务跟着移动（通过 parent_id 链）。"""
    note = await note_service.get_note(note_id)
    if not note:
        raise HTTPException(404, f"笔记不存在：{note_id}")
    if note.note_type != "task":
        raise HTTPException(400, "只有任务才能移动")
    # 如果指定了父任务，检查父任务存在
    if body.parent_id:
        parent = await note_service.get_note(body.parent_id)
        if not parent:
            raise HTTPException(404, f"父任务不存在：{body.parent_id}")
        if parent.note_type != "task":
            raise HTTPException(400, "目标不是任务")
        # 不能把任务移到自己或自己的后代下面
        if body.parent_id == note_id:
            raise HTTPException(400, "不能把任务移到自己下面")
        # 检查是否会形成循环
        current = body.parent_id
        seen = {note_id}
        while current:
            if current in seen:
                raise HTTPException(400, "不能形成循环：任务不能移动到自己的后代下面")
            seen.add(current)
            parent_note = await note_service.get_note(current)
            current = parent_note.parent_id if parent_note else None
    
    # 更新 parent_id
    note = await note_service.update_note(note_id, NoteUpdate(parent_id=body.parent_id))
    return note


# ─── 导入 Markdown ───────────────────────────────────────────────────────────
class PickPath(BaseModel):
    path: str


@router.get("/import/pick")
def pick_any():
    """统一的文件/文件夹选择框：先弹文件选择，取消后再弹文件夹选择"""
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        raise HTTPException(500, "当前 Python 环境没有 tkinter，无法弹出选择框，请手动输入路径")
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        chosen = filedialog.askopenfilename(
            title="选择 Markdown 文件，或点取消选择文件夹",
            filetypes=[("Markdown", "*.md *.markdown *.mdown *.mkd"), ("所有文件", "*.*")],
        )
        if not chosen:
            chosen = filedialog.askdirectory(title="选择 Markdown 文件夹")
    finally:
        root.destroy()
    return {"path": chosen or ""}


def _title_from(text: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def _convert_checklists(text: str) -> str:
    # 统一各种写法的任务复选框，保留缩进层级。
    # 注意只把 x/X/✓/✔ 当成已勾选，空格必须保持未勾选。
    def repl(m):
        checked = m.group(2) in "xX✓✔"
        # 列表符号可能是 - * +，统一成 -
        return f"{m.group(1)}- [{'x' if checked else ' '}] "
    return re.sub(r"^(\s*)[-*+](?:\s+[-*+])?\s*\[([^\]]?)\]\s?", repl, text, flags=re.MULTILINE)


def _join(path: str) -> str:
    """拼接路径时去掉重复的斜杠，保留中文和子目录"""
    return re.sub(r"/+", "/", path).lstrip("/")


def _collect_files(paths: List[str]):
    """展开文件或文件夹，返回 [(绝对路径, 相对导入根的子路径)]。跳过 node_modules / .git / dist 等目录。"""
    SKIP_DIRS = {'node_modules', '.git', 'dist', 'build', '__pycache__', '.venv', 'venv', '.idea', '.vscode'}
    out = []
    for raw in paths:
        p = Path(raw).expanduser()
        if not p.exists():
            continue
        if p.is_file():
            if p.suffix.lower() in MD_SUFFIXES:
                out.append((p, Path(p.name)))
        else:
            for f in sorted(p.rglob("*")):
                if not f.is_file() or f.suffix.lower() not in MD_SUFFIXES:
                    continue
                rel_parts = f.relative_to(p).parts
                if any(part.startswith(".") for part in rel_parts):
                    continue
                if any(part.lower() in SKIP_DIRS for part in rel_parts):
                    continue
                out.append((f, f.relative_to(p)))
    return out


@router.post("/import/")
async def import_markdown(req: ImportRequest):
    """把 Markdown 文件复制进知识库。只读取外部文件，不改动原文件。"""
    target_folder = (req.folder or "导入").strip().strip("/")
    files = _collect_files(req.files)
    if not files:
        raise HTTPException(400, "没有找到可导入的 .md 文件")

    imported, skipped, failed = [], [], []
    for src, rel in files:
        rel_path = rel if req.organize_subfolders else Path(rel.name)
        note_id = _join(f"{target_folder}/{rel_path.as_posix()}")
        target = note_service._file_path(note_id)
        if target.exists():
            if req.existing == "skip":
                skipped.append(str(rel))
                continue
            note_id = note_service._unique_id(note_id)
            target = note_service._file_path(note_id)
        try:
            text = src.read_text(encoding="utf-8-sig", errors="replace")
            if req.convert_checklists:
                text = _convert_checklists(text)
            note = await note_service.create_note(NoteCreate(
                id=note_id,
                title=_title_from(text, src.stem),
                content=text,
                tags=[],
                note_type="note",
            ))
            imported.append(note.id)
        except Exception as e:  # 单个文件失败不影响其他文件
            failed.append(f"{rel}: {e}")
    return {"imported": imported, "skipped": skipped, "failed": failed}
