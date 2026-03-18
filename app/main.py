from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from app.agents.medical import close_checkpointer, init_medical_agent
from app.core.config import settings
from app.observability.opik import configure_opik
from app.api.routes.threads import threads_router
from app.api.routes.chat import chat_router
from app.utils.logger import custom_logger


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_medical_agent()
    configure_opik()
    try:
        yield
    finally:
        await close_checkpointer()


app = FastAPI(
    title="Medical Info Agent",
    description="공공데이터 기반 의료 정보 조회 에이전트",
    version="0.1.0",
    lifespan=lifespan,
)

api_router = APIRouter(prefix=settings.API_V1_PREFIX)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_router.include_router(threads_router, tags=["threads"])
api_router.include_router(chat_router, tags=["chat"])

app.include_router(api_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    custom_logger.info(f"➡️ 요청 시작: {request.method} {request.url.path}")
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    custom_logger.info(
        f"⬅️ 요청 종료: {request.method} {request.url.path} "
        f"(실행 시간: {process_time:.3f}초) "
        f"상태코드: {response.status_code}"
    )

    return response


@app.get("/")
async def root():
    return {"message": "Medical Info Agent API", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
