import uuid
from app.services.threads_service import get_thread_by_id_json, get_threads_json, get_favorite_questions_json
from fastapi import APIRouter

from app.models.threads import RootBaseModel, ThreadDataResponse

threads_router = APIRouter()

@threads_router.get("/favorites/questions")
async def get_favorite_questions():
    """
    즐겨찾기된 질문 목록을 조회하는 API
    """
    favorite_questions = await get_favorite_questions_json()
    return favorite_questions


@threads_router.get("/threads")
async def get_all_threads():
    """
    최근 대화 목록을 조회하는 API
    """
    threads = await get_threads_json()
    return threads


@threads_router.get("/threads/{thread_id}", response_model=RootBaseModel[ThreadDataResponse])
async def get_thread_by_id(thread_id: uuid.UUID):
    """
    특정 대화 세션의 내용을 조회하는 API
    """
    messages = await get_thread_by_id_json(thread_id)
    return messages
