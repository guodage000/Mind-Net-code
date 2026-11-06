from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class NoteBase(BaseModel):
    title: str
    content: str = ""
    tags: List[str] = []
    note_type: str = "note"       # note | task | ai_summary
    status: Optional[str] = None  # todo | in_progress | done | blocked
    priority: Optional[str] = None  # low | medium | high
    deadline: Optional[str] = None
    parent_id: Optional[str] = None


class NoteCreate(NoteBase):
    id: Optional[str] = None  # 传路径；不传则自动生成


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    deadline: Optional[str] = None
    parent_id: Optional[str] = None


class Note(NoteBase):
    id: str
    created_at: str
    updated_at: str
    subtask_ids: List[str] = []  # 子任务笔记的 id 列表（通过 parent_id 关联）

    class Config:
        from_attributes = True


class SearchResult(BaseModel):
    id: str
    title: str
    snippet: str       # 匹配上下文片段
    tags: List[str]
    note_type: str
    updated_at: str
    score: float = 0.0


class SearchQuery(BaseModel):
    q: str
    tags: List[str] = []
    note_type: Optional[str] = None
    limit: int = 20
    offset: int = 0


class FileTreeNode(BaseModel):
    name: str
    path: str
    is_dir: bool
    note_type: Optional[str] = None  # 文件的笔记类型：note | task | ai_summary，文件夹为 None
    children: List["FileTreeNode"] = []

FileTreeNode.model_rebuild()


class GitStatus(BaseModel):
    enabled: bool
    remote: str
    branch: str
    pending_changes: int
    last_sync: Optional[str] = None
    error: Optional[str] = None
