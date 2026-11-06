from fastapi import APIRouter
from app.models.schemas import SearchQuery, SearchResult
from app.services.note_service import search_notes, get_all_tags
from typing import List

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/", response_model=List[SearchResult])
def search(query: SearchQuery):
    return search_notes(query)


@router.get("/tags")
def tags():
    return get_all_tags()
