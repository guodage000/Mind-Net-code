from pydantic import BaseModel
from typing import Optional, List


class TaskItem(BaseModel):
    id: str
    title: str
    status: str            # todo | in_progress | done | blocked
    priority: Optional[str] = None
    deadline: Optional[str] = None
    time: Optional[str] = None          # 正文里最早的时间，如 "18:00"
    tags: List[str] = []
    updated_at: str
    total: int = 0         # 正文里任务复选框总数
    finished: int = 0      # 其中已勾选的数量
    hasSubtasks: bool = False           # 是否有缩进的子任务
    subtaskIds: List[str] = []          # 子任务笔记的 id 列表（独立文件）
    parentId: Optional[str] = None      # 父任务 id（如果有）


class TaskSummary(BaseModel):
    tasks: List[TaskItem]
    counts: dict           # 各状态的任务数


class MoveTask(BaseModel):
    parent_id: Optional[str] = None  # None 表示变成顶层任务，否则变成那个任务的子任务


class ImportRequest(BaseModel):
    folder: str = "导入"            # 导入到哪个文件夹（在 vault 内）
    files: List[str] = []          # 要导入的本地文件或文件夹路径
    organize_subfolders: bool = True  # 导入文件夹时，按子文件夹保留层级
    convert_checklists: bool = True   # 把 "- [x]" 统一成任务复选框格式
    existing: str = "rename"       # 重名时：rename 加序号 / skip 跳过
