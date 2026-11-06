from fastapi import APIRouter, HTTPException
from app.models.schemas import Note, NoteCreate, NoteUpdate, FileTreeNode
from app.services import note_service

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/tree", response_model=FileTreeNode)
def file_tree(sub: str = ""):
    return note_service.get_file_tree(sub)


# 必须放在 /{note_id:path} 之前，否则会被当成笔记路径的一部分
@router.get("/{note_id:path}/backlinks")
async def backlinks(note_id: str):
    return {"backlinks": note_service.get_backlinks(note_id)}


@router.get("/{note_id:path}", response_model=Note)
async def get_note(note_id: str):
    note = await note_service.get_note(note_id)
    if not note:
        raise HTTPException(404, f"笔记不存在：{note_id}")
    return note


@router.post("/", response_model=Note, status_code=201)
async def create_note(data: NoteCreate):
    return await note_service.create_note(data)


@router.patch("/{note_id:path}", response_model=Note)
async def update_note(note_id: str, data: NoteUpdate):
    note = await note_service.update_note(note_id, data)
    if not note:
        raise HTTPException(404, f"笔记不存在：{note_id}")
    return note


@router.delete("/{note_id:path}", status_code=204)
async def delete_note(note_id: str):
    ok = await note_service.delete_note(note_id)
    if not ok:
        raise HTTPException(404, f"笔记不存在：{note_id}")
