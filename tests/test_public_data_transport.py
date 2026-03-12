import pytest

from app.infrastructure.public_data.transport import (
    close_public_data_http_client,
    get_public_data_http_client,
)


@pytest.mark.asyncio
async def test_public_data_http_client_is_reused():
    client1 = await get_public_data_http_client()
    client2 = await get_public_data_http_client()

    assert client1 is client2

    await close_public_data_http_client()
