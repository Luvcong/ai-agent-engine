import uuid
from app.models.threads import RootBaseModel, ThreadDataResponse
from app.utils.read_json import read_json


# 즐겨찾기 질문 목록 JSON 파일을 읽어 반환한다.
async def get_favorite_questions_json():
    return read_json("favorite_questions.json")


# 전체 스레드 목록 JSON 파일을 읽어 반환한다.
async def get_threads_json():
    return read_json("threads.json")


# 스레드 ID에 해당하는 JSON 파일을 읽어 응답 모델 형태로 감싸 반환한다.
async def get_thread_by_id_json(thread_id: uuid.UUID):
    json_data = read_json(f"threads/{str(thread_id)}.json")
    thread_data = ThreadDataResponse(**json_data)
    return RootBaseModel[ThreadDataResponse](response=thread_data)
