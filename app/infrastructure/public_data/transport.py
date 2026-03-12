from __future__ import annotations

from typing import Any

import httpx

from app.infrastructure.public_data.parsers import parse_public_data_response

_shared_public_data_http_client: httpx.AsyncClient | None = None


async def init_public_data_http_client() -> httpx.AsyncClient:
    global _shared_public_data_http_client
    if _shared_public_data_http_client is None:
        _shared_public_data_http_client = httpx.AsyncClient(
            follow_redirects=True,
        )
    return _shared_public_data_http_client


async def close_public_data_http_client() -> None:
    global _shared_public_data_http_client
    if _shared_public_data_http_client is not None:
        await _shared_public_data_http_client.aclose()
        _shared_public_data_http_client = None


async def get_public_data_http_client() -> httpx.AsyncClient:
    if _shared_public_data_http_client is None:
        return await init_public_data_http_client()
    return _shared_public_data_http_client


async def request_public_data(
    *,
    base_url: str,
    endpoint: str,
    params: dict[str, Any],
    service_key: str,
    timeout: int,
) -> dict[str, Any]:
    if not service_key:
        raise ValueError("PUBLIC_DATA_API_KEY is not configured.")

    request_params = {
        "serviceKey": service_key,
        "_type": "json",
        **params,
    }
    client = await get_public_data_http_client()
    response = await client.get(
        f"{base_url}{endpoint}",
        params=request_params,
        timeout=timeout,
    )
    if response.status_code == 401:
        raise ValueError(
            "공공데이터 API 인증에 실패했습니다. PUBLIC_DATA_API_KEY 값을 확인하세요."
        )
    response.raise_for_status()
    return parse_public_data_response(response)
