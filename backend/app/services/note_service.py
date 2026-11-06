import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import aiofiles

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import Note, NoteCreate, NoteUpdate, SearchResult, SearchQuery, FileTreeNode


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_frontmatter(raw: str) -> tuple[dict, str]:
    """解析 YAML frontmatter，返回 (meta, body)"""
    meta = {}
    body = raw
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            fm_text = raw[3:end].strip()
            body = raw[end + 4:].lstrip("\n")
            for line in fm_text.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    k, v = k.strip(), v.strip()
                    if v.startswith("[") and v.endswith("]"):
                        meta[k] = [x.strip().strip('"').strip("'")
                                   for x in v[1:-1].split(",") if x.strip()]
                    elif k == "tags" and isinstance(v, str):
                        # 支持全角逗号、分号、顿号分隔的标签
                        meta[k] = [x.strip() for x in re.split(r"[,，;；、]", v) if x.strip()]
                    else:
                        meta[k] = v.strip('"').strip("'")
    return meta, body


def _build_frontmatter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            lines.append(f"{k}: [{', '.join(v)}]")
        elif v is not None:
            lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


_DEFAULT_FOLDERS = {"note": "笔记", "task": "任务", "ai_summary": "AI总结"}


def _normalize_id(note_id: str) -> str:
    """统一笔记 id：正斜杠、去掉开头斜杠、补全 .md"""
    nid = (note_id or "").replace("\\", "/").strip().lstrip("/")
    if not nid:
        raise ValueError("笔记路径不能为空")
    if not nid.lower().endswith(".md"):
        nid += ".md"
    return nid


def _file_path(note_id: str) -> Path:
    """note_id 是相对 vault 的路径，如 固件/光源模块/PWM调光.md。拒绝跳出 vault 的路径。"""
    vault = settings.vault_path.resolve()
    p = (vault / _normalize_id(note_id)).resolve()
    try:
        p.relative_to(vault)
    except ValueError:
        raise ValueError(f"非法路径：{note_id}")
    return p


def _safe_stem(name: str) -> str:
    stem = re.sub(r'[\\/:*?"<>|]', "_", name).strip().rstrip(". ")
    return stem or "未命名"


def _unique_id(note_id: str) -> str:
    """文件已存在时自动加 -2、-3，避免新建笔记覆盖已有笔记"""
    nid = _normalize_id(note_id)
    folder, _, filename = nid.rpartition("/")
    stem = _safe_stem(filename[:-3])
    base = f"{folder}/{stem}" if folder else stem
    candidate = f"{base}.md"
    n = 2
    while _file_path(candidate).exists():
        candidate = f"{base}-{n}.md"
        n += 1
    return candidate


def _extract_links(content: str) -> List[str]:
    """提取 [[链接]] 格式的双向链接目标"""
    return re.findall(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]", content)


def checklist_stats(content: str) -> tuple[int, int]:
    """返回 (任务复选框总数, 已勾选数量)"""
    boxes = re.findall(r"^\s*[-*+]\s+\[([ xX])\]", content, re.MULTILINE)
    return len(boxes), sum(1 for b in boxes if b.lower() == "x")


def _find_subtasks(note_id: str) -> List[str]:
    """从索引里找这篇笔记的子任务（按 parent_id 关联）"""
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id FROM notes WHERE parent_id=? ORDER BY updated_at DESC", (note_id,)
        ).fetchall()
        return [r["id"] for r in rows]
    finally:
        conn.close()


# ─── CRUD ────────────────────────────────────────────────────────────────────

async def get_note(note_id: str) -> Optional[Note]:
    note_id = _normalize_id(note_id)
    fp = _file_path(note_id)
    if not fp.exists():
        return None
    async with aiofiles.open(fp, "r", encoding="utf-8") as f:
        raw = await f.read()
    meta, body = _parse_frontmatter(raw)
    title = meta.get("title", fp.stem)
    subtask_ids = _find_subtasks(note_id) if meta.get("type", "note") == "task" else []
    return Note(
        id=note_id,
        title=title,
        content=body,
        tags=meta.get("tags", []) if isinstance(meta.get("tags"), list) else [],
        note_type=meta.get("type", "note"),
        status=meta.get("status"),
        priority=meta.get("priority"),
        deadline=meta.get("deadline"),
        parent_id=meta.get("parent_id"),
        created_at=meta.get("created_at", _now_iso()),
        updated_at=meta.get("updated_at", _now_iso()),
        subtask_ids=subtask_ids,
    )


async def create_note(data: NoteCreate) -> Note:
    now = _now_iso()
    folder = _DEFAULT_FOLDERS.get(data.note_type, "笔记")
    
    # 如果有父任务，子任务放在父任务的同名文件夹里
    if data.parent_id and data.note_type == "task":
        parent_fp = _file_path(data.parent_id)
        if parent_fp.exists():
            parent_folder = parent_fp.stem
            parent_dir = parent_fp.parent
            folder_path = f"{parent_dir.relative_to(settings.vault_path).as_posix()}/{parent_folder}"
            note_id = _unique_id(f"{folder_path}/{data.title}")
        else:
            note_id = _unique_id(data.id or f"{folder}/{data.title}")
    else:
        note_id = _unique_id(data.id or f"{folder}/{data.title}")
    
    fp = _file_path(note_id)
    fp.parent.mkdir(parents=True, exist_ok=True)

    meta = {
        "title": data.title,
        "type": data.note_type,
        "tags": data.tags,
        "created_at": now,
        "updated_at": now,
    }
    # 任务笔记必须带状态：没设过的默认待做，设成"待做"时也要写进去而不是省略
    if data.note_type == "task":
        meta["status"] = data.status or "todo"
    if data.status:
        meta["status"] = data.status
    if data.priority:
        meta["priority"] = data.priority
    if data.deadline:
        meta["deadline"] = data.deadline
    if data.parent_id:
        meta["parent_id"] = data.parent_id

    raw = _build_frontmatter(meta) + data.content
    async with aiofiles.open(fp, "w", encoding="utf-8") as f:
        await f.write(raw)

    # 从磁盘读回来返回，保证响应和文件内容一致（例如任务的默认状态）
    note = await get_note(note_id)
    if note:
        _index_note(note)
        return note
    return Note(id=note_id, created_at=now, updated_at=now, **data.model_dump(exclude={"id"}))


async def update_note(note_id: str, data: NoteUpdate) -> Optional[Note]:
    existing = await get_note(note_id)
    if not existing:
        return None
    now = _now_iso()
    fp = _file_path(note_id)

    # 用 exclude_unset 保留显式传的 None（比如 parent_id=None 表示变成顶层任务）
    updated = existing.model_copy(update={k: v for k, v in data.model_dump(exclude_unset=True).items()})
    updated = updated.model_copy(update={"updated_at": now})

    meta = {
        "title": updated.title,
        "type": updated.note_type,
        "tags": updated.tags,
        "created_at": updated.created_at,
        "updated_at": now,
    }
    for field in ("status", "priority", "deadline"):
        val = getattr(updated, field)
        if val:
            meta[field] = val
    # parent_id 特殊处理：显式传 None 表示变成顶层任务
    if "parent_id" in data.model_dump(exclude_unset=True):
        if data.parent_id:
            meta["parent_id"] = data.parent_id
        # 显式传 None 时不写 parent_id，表示变成顶层任务
    elif updated.parent_id:
        meta["parent_id"] = updated.parent_id
    # 任务笔记状态不能丢，设成"待做"时也要写回
    if updated.note_type == "task":
        meta["status"] = updated.status or "todo"

    raw = _build_frontmatter(meta) + (data.content if data.content is not None else existing.content)
    async with aiofiles.open(fp, "w", encoding="utf-8") as f:
        await f.write(raw)

    _index_note(updated)
    return updated


async def delete_note(note_id: str) -> bool:
    note_id = _normalize_id(note_id)
    fp = _file_path(note_id)
    if not fp.exists():
        return False
    fp.unlink()
    _deindex_note(note_id)
    # 清理删除后留下的空文件夹，不会删到 vault 根目录
    vault = settings.vault_path.resolve()
    parent = fp.parent
    while parent != vault and vault in parent.parents:
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent
    return True


# ─── 文件树 ───────────────────────────────────────────────────────────────────

def _note_types() -> dict:
    """从索引里读所有文件的笔记类型，用于文件树标记任务"""
    conn = get_db()
    try:
        rows = conn.execute("SELECT id, note_type FROM notes").fetchall()
        return {r["id"]: r["note_type"] for r in rows}
    finally:
        conn.close()


def get_file_tree(sub: str = "") -> FileTreeNode:
    root = settings.vault_path / sub if sub else settings.vault_path
    root.mkdir(parents=True, exist_ok=True)
    types = _note_types()
    return _build_tree(root, settings.vault_path, types)


def _build_tree(path: Path, vault_root: Path, types: dict) -> FileTreeNode:
    rel = str(path.relative_to(vault_root)).replace("\\", "/")
    note_type = None if path.is_dir() else types.get(rel, "note")
    node = FileTreeNode(name=path.name or "vault", path=rel or ".", is_dir=path.is_dir(), note_type=note_type)
    if path.is_dir():
        children = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        node.children = [_build_tree(c, vault_root, types) for c in children
                         if not c.name.startswith(".")]
    return node


# ─── 全文索引 ─────────────────────────────────────────────────────────────────

def _index_note(note: Note):
    conn = get_db()
    try:
        tags_json = json.dumps(note.tags, ensure_ascii=False)
        conn.execute(
            "INSERT OR REPLACE INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (note.id, note.title, note.content, tags_json,
             note.status, note.priority, note.deadline,
             note.parent_id, note.note_type,
             note.created_at, note.updated_at)
        )
        conn.execute("DELETE FROM notes_fts WHERE id=?", (note.id,))
        conn.execute(
            "INSERT INTO notes_fts(id,title,content,tags) VALUES (?,?,?,?)",
            (note.id, note.title, note.content, " ".join(note.tags))
        )
        # 更新标签计数
        conn.execute("DELETE FROM tags WHERE name NOT IN "
                     "(SELECT DISTINCT json_each.value FROM notes, json_each(notes.tags))")
        for tag in note.tags:
            conn.execute("INSERT OR IGNORE INTO tags(name,count) VALUES(?,0)", (tag,))
            conn.execute("UPDATE tags SET count = (SELECT COUNT(*) FROM notes WHERE tags LIKE ?) WHERE name=?",
                         (f'%"{tag}"%', tag))
        # 双向链接
        conn.execute("DELETE FROM links WHERE source_id=?", (note.id,))
        for target in _extract_links(note.content):
            conn.execute("INSERT OR IGNORE INTO links VALUES (?,?)", (note.id, target))
        conn.commit()
    finally:
        conn.close()


def _deindex_note(note_id: str):
    conn = get_db()
    try:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
        conn.execute("DELETE FROM notes_fts WHERE id=?", (note_id,))
        conn.execute("DELETE FROM links WHERE source_id=? OR target_id=?", (note_id, note_id))
        conn.commit()
    finally:
        conn.close()


def search_notes(query: SearchQuery) -> List[SearchResult]:
    conn = get_db()
    try:
        params: list = []
        sql = """
            SELECT n.id, n.title, n.tags, n.note_type, n.updated_at,
                   snippet(notes_fts, 2, '<mark>', '</mark>', '...', 20) AS snippet,
                   bm25(notes_fts) AS score
            FROM notes_fts
            JOIN notes n ON notes_fts.id = n.id
            WHERE notes_fts MATCH ?
        """
        params.append(query.q)
        if query.note_type:
            sql += " AND n.note_type = ?"
            params.append(query.note_type)
        if query.tags:
            for tag in query.tags:
                sql += ' AND n.tags LIKE ?'
                params.append(f'%"{tag}"%')
        sql += " ORDER BY score LIMIT ? OFFSET ?"
        params += [query.limit, query.offset]

        rows = conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            results.append(SearchResult(
                id=r["id"], title=r["title"],
                snippet=r["snippet"] or "",
                tags=json.loads(r["tags"]),
                note_type=r["note_type"],
                updated_at=r["updated_at"],
                score=abs(r["score"]),
            ))
        return results
    finally:
        conn.close()


def get_all_tags() -> List[dict]:
    conn = get_db()
    try:
        rows = conn.execute("SELECT name, count FROM tags ORDER BY count DESC").fetchall()
        return [{"name": r["name"], "count": r["count"]} for r in rows]
    finally:
        conn.close()


def get_backlinks(note_id: str) -> List[str]:
    conn = get_db()
    try:
        rows = conn.execute("SELECT source_id FROM links WHERE target_id=?", (note_id,)).fetchall()
        return [r["source_id"] for r in rows]
    finally:
        conn.close()


async def rebuild_index():
    """扫描 vault 所有 .md 文件，重建索引；文件已不存在的笔记从索引里移除"""
    on_disk = set()
    for fp in settings.vault_path.rglob("*.md"):
        rel = fp.relative_to(settings.vault_path)
        if any(part.startswith(".") for part in rel.parts):
            continue
        note_id = str(rel).replace("\\", "/")
        on_disk.add(note_id)
        note = await get_note(note_id)
        if note:
            _index_note(note)

    conn = get_db()
    try:
        indexed = [r["id"] for r in conn.execute("SELECT id FROM notes").fetchall()]
    finally:
        conn.close()
    for note_id in indexed:
        if note_id not in on_disk:
            _deindex_note(note_id)
