import asyncio
import logging, time, inspect
from functools import wraps

# 공통 포맷 설정
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
)

custom_logger = logging.getLogger("edu_agent")


def log_execution(func):
    """
    Executes logging for all types:
    - async generator
    - async function
    - sync generator
    - sync function
    while preserving original return types.
    """

    # ---------------------------
    # 1) ASYNC GENERATOR FUNCTION
    # ---------------------------
    if inspect.isasyncgenfunction(func):

        @wraps(func)
        async def async_gen_wrapper(*args, **kwargs):
            custom_logger.info(f"▶️ 시작: {func.__name__}")
            start = time.time()

            try:
                async for item in func(*args, **kwargs):
                    yield item
            except Exception as e:
                custom_logger.error(f"❌ 오류: {func.__name__} - {e}")
                raise
            finally:
                elapsed = time.time() - start
                custom_logger.info(f"✅ 종료: {func.__name__} (실행 시간: {elapsed:.3f}초)")

        return async_gen_wrapper

    # -----------------------
    # 2) ASYNC NORMAL FUNCTION
    # -----------------------
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def async_func_wrapper(*args, **kwargs):
            custom_logger.info(f"▶️ 시작: {func.__name__}")
            start = time.time()

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                custom_logger.error(f"❌ 오류: {func.__name__} - {e}")
                raise
            finally:
                elapsed = time.time() - start
                custom_logger.info(f"✅ 종료: {func.__name__} (실행 시간: {elapsed:.3f}초)")

        return async_func_wrapper

    # ---------------------------
    # 3) SYNC GENERATOR FUNCTION
    # ---------------------------
    if inspect.isgeneratorfunction(func):

        @wraps(func)
        def gen_wrapper(*args, **kwargs):
            custom_logger.info(f"▶️ 시작: {func.__name__}")
            start = time.time()

            try:
                for item in func(*args, **kwargs):
                    yield item
            except Exception as e:
                custom_logger.error(f"❌ 오류: {func.__name__} - {e}")
                raise
            finally:
                elapsed = time.time() - start
                custom_logger.info(f"✅ 종료: {func.__name__} (실행 시간: {elapsed:.3f}초)")

        return gen_wrapper

    # --------------------
    # 4) SYNC NORMAL FUNCTION
    # --------------------
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        custom_logger.info(f"▶️ 시작: {func.__name__}")
        start = time.time()

        try:
            return func(*args, **kwargs)
        except Exception as e:
            custom_logger.error(f"❌ 오류: {func.__name__} - {e}")
            raise
        finally:
            elapsed = time.time() - start
            custom_logger.info(f"✅ 종료: {func.__name__} (실행 시간: {elapsed:.3f}초)")

    return func_wrapper
