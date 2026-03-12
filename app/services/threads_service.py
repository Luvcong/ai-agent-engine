import uuid
from app.models.threads import RootBaseModel, ThreadDataResponse
from app.utils.read_json import read_json


async def get_favorite_questions_json():
    return read_json("favorite_questions.json")


async def get_threads_json():
    return read_json("threads.json")


async def get_thread_by_id_json(thread_id: uuid.UUID):
    json_data = read_json(f"threads/{str(thread_id)}.json")
    thread_data = ThreadDataResponse(**json_data)
    return RootBaseModel[ThreadDataResponse](response=thread_data)
