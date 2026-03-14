import json
import uuid

import pytest
from fastapi.testclient import TestClient
import httpx

from app.clients.elasticsearch import ElasticDiseaseSearchClient
from app.clients.public_data import PublicMedicalDataClient
from app.core.config import settings
from app.services.agent_service import AgentService
from app.tools.medical_tools import (
    resolve_region_information,
    search_disease_knowledge,
    search_disease_info,
    search_drug_info,
    search_hospital_info,
    search_pharmacy_info,
)


def parse_sse_response(response_text: str) -> list[dict]:
    events = []
    for line in response_text.strip().split("\n"):
        if not line.startswith("data: "):
            continue
        events.append(json.loads(line[6:]))
    return events


def test_chat_stream_returns_sse_events(client: TestClient, monkeypatch):
    async def fake_process_query(self, user_messages: str, thread_id: uuid.UUID):
        yield json.dumps(
            {"step": "model", "tool_calls": ["search_drug_info"]},
            ensure_ascii=False,
        )
        yield json.dumps(
            {
                "step": "tools",
                "name": "search_drug_info",
                "content": {
                    "query": {"item_name": "타이레놀"},
                    "count": 1,
                    "items": [{"item_name": "타이레놀정160mg"}],
                },
            },
            ensure_ascii=False,
        )
        yield json.dumps(
            {
                "step": "done",
                "message_id": str(uuid.uuid4()),
                "role": "assistant",
                "content": "타이레놀 정보를 찾았습니다.",
                "metadata": {
                    "tool_name": "search_drug_info",
                    "query": {"item_name": "타이레놀"},
                    "result": {"count": 1},
                },
                "created_at": "2026-03-11T00:00:00",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(AgentService, "process_query", fake_process_query)

    response = client.post(
        "/api/v1/chat",
        json={
            "thread_id": str(uuid.uuid4()),
            "message": "타이레놀이 어떤 약인지 알려줘",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    events = parse_sse_response(response.text)
    assert events[0]["tool_calls"] in (
        ["요청하신 내용을 확인하고 있습니다."],
        ["Planning"],
    )
    assert events[1]["tool_calls"] == ["search_drug_info"]
    assert events[2]["name"] == "search_drug_info"
    assert events[3]["step"] == "done"
    assert events[3]["metadata"]["tool_name"] == "search_drug_info"


@pytest.mark.asyncio
async def test_drug_tool_uses_public_client(monkeypatch):
    async def fake_search_drugs(self, **kwargs):
        return {
            "query": kwargs,
            "count": 1,
            "items": [{"item_name": "타이레놀정160mg"}],
        }

    monkeypatch.setattr(PublicMedicalDataClient, "search_drugs", fake_search_drugs)

    result = await search_drug_info.ainvoke(
        {"item_name": "타이레놀", "enterprise_name": "한국얀센", "limit": 3}
    )

    assert result["count"] == 1
    assert result["query"]["item_name"] == "타이레놀"
    assert result["items"][0]["item_name"] == "타이레놀정160mg"


@pytest.mark.asyncio
async def test_disease_tool_uses_public_client(monkeypatch):
    async def fake_search_diseases(self, **kwargs):
        return {
            "query": kwargs,
            "count": 1,
            "items": [{"disease_code": "J00", "disease_name": "감기"}],
        }

    monkeypatch.setattr(
        PublicMedicalDataClient,
        "search_diseases",
        fake_search_diseases,
    )

    result = await search_disease_info.ainvoke(
        {"disease_name": "감기", "limit": 2}
    )

    assert result["count"] == 1
    assert result["items"][0]["disease_code"] == "J00"


@pytest.mark.asyncio
async def test_elastic_disease_tool_uses_search_client(monkeypatch):
    async def fake_search_disease_knowledge(self, **kwargs):
        return {
            "query": kwargs,
            "count": 1,
            "items": [
                {
                    "document_id": "433765_1",
                    "content": "2형 당뇨병 환자는 혈당 조절을 통해 합병증을 예방해야 합니다.",
                }
            ],
        }

    monkeypatch.setattr(
        ElasticDiseaseSearchClient,
        "search_disease_knowledge",
        fake_search_disease_knowledge,
    )

    result = await search_disease_knowledge.ainvoke(
        {
            "query": "2형 당뇨병 치료 원칙",
            "source_spec": "대한의학회",
            "limit": 3,
        }
    )

    assert result["count"] == 1
    assert result["query"]["query"] == "2형 당뇨병 치료 원칙"
    assert result["items"][0]["document_id"] == "433765_1"


@pytest.mark.asyncio
async def test_disease_client_uses_search_text_params(monkeypatch):
    captured = {}

    async def fake_request(self, *, base_url, endpoint, params):
        captured["base_url"] = base_url
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {"sickCd": "H10", "sickNm": "결막염", "sickNmEng": None}
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(PublicMedicalDataClient, "_request", fake_request)

    client = PublicMedicalDataClient()
    result = await client.search_diseases(query="결막염", limit=3)

    assert captured["endpoint"] == "/getDissNameCodeList1"
    assert captured["params"]["diseaseType"] == "SICK_NM"
    assert captured["params"]["searchText"] == "결막염"
    assert captured["params"]["medTp"] == "1"
    assert result["items"][0]["disease_code"] == "H10"


@pytest.mark.asyncio
async def test_public_client_returns_friendly_message_for_connect_error(monkeypatch):
    async def fake_get(self, endpoint, params=None):
        raise httpx.ConnectError("dns failed")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    client = PublicMedicalDataClient()

    with pytest.raises(ValueError) as exc_info:
        await client.search_hospitals(hospital_name="성모온정신건강의학과", limit=1)

    assert "네트워크 또는 DNS 설정" in str(exc_info.value)


@pytest.mark.asyncio
async def test_elastic_client_builds_search_payload(monkeypatch):
    captured = {}

    monkeypatch.setattr(settings, "ELASTICSEARCH_URL", "https://example.com")
    monkeypatch.setattr(settings, "ELASTICSEARCH_INDEX", "edu-collection")
    monkeypatch.setattr(settings, "ELASTICSEARCH_USERNAME", "elastic")
    monkeypatch.setattr(settings, "ELASTICSEARCH_PASSWORD", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["payload"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "hits": {
                    "hits": [
                        {
                            "_index": "edu-collection",
                            "_id": "433765_1",
                            "_score": 4.2,
                            "_source": {
                                "c_id": ["433765_1"],
                                "domain": [2],
                                "source": [4],
                                "source_spec": ["대한의학회"],
                                "creation_year": ["2022"],
                                "content": [
                                    "2형 당뇨병 환자는 혈당 조절을 통해 당뇨병 합병증을 예방해야 합니다."
                                ],
                            },
                            "highlight": {
                                "content": [
                                    "<em>당뇨병</em> 환자는 혈당 조절을 통해 합병증을 예방해야 합니다."
                                ]
                            },
                        }
                    ]
                }
            },
        )

    transport = httpx.MockTransport(handler)
    original_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs["transport"] = transport
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)

    client = ElasticDiseaseSearchClient()
    result = await client.search_disease_knowledge(
        query="2형 당뇨병 치료",
        domain=2,
        source=4,
        source_spec="대한의학회",
        creation_year="2022",
        limit=2,
    )

    assert captured["method"] == "POST"
    assert captured["url"].endswith("/edu-collection/_search")
    assert '"query":"2형 당뇨병 치료"' in captured["payload"]
    assert '"match_phrase":{"source_spec":"대한의학회"}' in captured["payload"]
    assert result["count"] == 1
    assert result["items"][0]["document_id"] == "433765_1"
    assert result["items"][0]["source_spec"] == "대한의학회"
    assert result["items"][0]["excerpt"].startswith("<em>당뇨병</em>")


@pytest.mark.asyncio
async def test_hospital_tool_uses_public_client(monkeypatch):
    async def fake_search_hospitals(self, **kwargs):
        return {
            "query": kwargs,
            "count": 1,
            "items": [{"hospital_name": "서울아산병원"}],
        }

    monkeypatch.setattr(
        PublicMedicalDataClient,
        "search_hospitals",
        fake_search_hospitals,
    )

    result = await search_hospital_info.ainvoke(
        {
            "hospital_name": "서울아산병원",
            "region_keyword": "서울",
            "department_name": "정형외과",
            "hospital_type_name": "종합병원",
            "limit": 2,
        }
    )

    assert result["count"] == 1
    assert result["items"][0]["hospital_name"] == "서울아산병원"
    assert result["query"]["department_name"] == "정형외과"
    assert result["query"]["hospital_type_name"] == "종합병원"


@pytest.mark.asyncio
async def test_pharmacy_tool_uses_public_client(monkeypatch):
    async def fake_search_pharmacies(self, **kwargs):
        return {
            "query": kwargs,
            "count": 1,
            "items": [{"pharmacy_name": "온누리건강약국"}],
        }

    monkeypatch.setattr(
        PublicMedicalDataClient,
        "search_pharmacies",
        fake_search_pharmacies,
    )

    result = await search_pharmacy_info.ainvoke(
        {
            "pharmacy_name": "온누리건강약국",
            "region_keyword": "서울 중랑구",
            "limit": 2,
        }
    )

    assert result["count"] == 1
    assert result["items"][0]["pharmacy_name"] == "온누리건강약국"
    assert result["query"]["region_keyword"] == "서울 중랑구"


@pytest.mark.asyncio
async def test_hospital_client_supports_region_and_department(monkeypatch):
    captured = {}

    async def fake_request(self, *, base_url, endpoint, params):
        captured["base_url"] = base_url
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "yadmNm": "구로디지털정형외과의원",
                                "clCdNm": "의원",
                                "sidoCdNm": "서울특별시",
                                "sgguCdNm": "관악구",
                                "emdongNm": "신림동",
                                "addr": "서울특별시 관악구 조원로 20, 2층 (신림동)",
                                "telno": "02-869-1020",
                                "hospUrl": None,
                                "estbDd": 20230126,
                                "XPos": 126.9045681,
                                "YPos": 37.4832771,
                            }
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(PublicMedicalDataClient, "_request", fake_request)

    client = PublicMedicalDataClient()
    result = await client.search_hospitals(
        hospital_name=None,
        region_keyword="구로디지털",
        hospital_type_name="의원",
        department_name="정형외과",
        x_pos=126.90,
        y_pos=37.48,
        radius=1000,
        limit=10,
    )

    assert captured["endpoint"] == "/getHospBasisList"
    assert captured["params"]["clCd"] == "71"
    assert captured["params"]["dgsbjtCd"] == "05"
    assert captured["params"]["xPos"] == "126.9"
    assert captured["params"]["yPos"] == "37.48"
    assert captured["params"]["radius"] == "1000"
    assert result["count"] == 1
    assert result["items"][0]["hospital_name"] == "구로디지털정형외과의원"
    assert result["items"][0]["sido_name"] == "서울특별시"
    assert result["items"][0]["sggu_name"] == "관악구"
    assert result["items"][0]["emdong_name"] == "신림동"


@pytest.mark.asyncio
async def test_pharmacy_client_supports_region_and_radius(monkeypatch):
    captured = {}

    async def fake_request(self, *, base_url, endpoint, params):
        captured["base_url"] = base_url
        captured["endpoint"] = endpoint
        captured["params"] = params
        return {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "yadmNm": "온누리건강약국",
                                "sidoCdNm": "서울특별시",
                                "sgguCdNm": "중랑구",
                                "emdongNm": "신내동",
                                "addr": "서울특별시 중랑구 신내로 72",
                                "telno": "02-123-4567",
                                "hospUrl": None,
                                "postNo": "02000",
                                "XPos": 127.0965441,
                                "YPos": 37.6076556,
                            }
                        ]
                    }
                }
            }
        }

    monkeypatch.setattr(PublicMedicalDataClient, "_request", fake_request)

    client = PublicMedicalDataClient()
    result = await client.search_pharmacies(
        pharmacy_name=None,
        region_keyword="서울 중랑구 신내동",
        x_pos=127.09,
        y_pos=37.60,
        radius=3000,
        limit=10,
    )

    assert captured["base_url"] == client.PHARMACY_BASE_URL
    assert captured["endpoint"] == "/getParmacyBasisList"
    assert captured["params"]["sidoCd"] == "110000"
    assert captured["params"]["sgguCd"] == "110019"
    assert captured["params"]["emdongNm"] == "신내동"
    assert captured["params"]["xPos"] == "127.09"
    assert captured["params"]["yPos"] == "37.6"
    assert captured["params"]["radius"] == "3000"
    assert result["count"] == 1
    assert result["items"][0]["pharmacy_name"] == "온누리건강약국"
    assert result["items"][0]["sggu_name"] == "중랑구"


def test_hospital_client_filters_region_keyword():
    client = PublicMedicalDataClient()
    items = [
        {"yadmNm": "구로디지털정형외과의원", "addr": "서울특별시 관악구 조원로 20"},
        {"yadmNm": "반도정형외과병원", "addr": "서울특별시 중구 동호로 202"},
    ]

    filtered = client._filter_hospital_items(items, region_keyword="구로디지털")

    assert len(filtered) == 1
    assert filtered[0]["yadmNm"] == "구로디지털정형외과의원"


def test_hospital_client_prefers_department_name_matches():
    client = PublicMedicalDataClient()
    items = [
        {"yadmNm": "윤안과의원", "addr": "서울 성동구 금호동4가"},
        {"yadmNm": "금호퍼스트내과의원", "addr": "서울 성동구 금호동4가"},
        {"yadmNm": "성모우리이비인후과의원", "addr": "서울 성동구 금호동1가"},
    ]

    filtered = client._prefer_department_name_matches(items, department_name="안과")

    assert len(filtered) == 1
    assert filtered[0]["yadmNm"] == "윤안과의원"


def test_hospital_client_parses_combined_search_text():
    client = PublicMedicalDataClient()

    parsed = client._parse_hospital_search_text(
        hospital_name="구로디지털 정형외과",
        region_keyword=None,
        department_name=None,
    )

    assert parsed == ("구로디지털정형외과", "구로디지털", "정형외과")


def test_hospital_client_resolves_region_codes():
    client = PublicMedicalDataClient()

    resolved = client._resolve_region_codes(
        region_keyword="서울 구로구 구로디지털",
        sido_code=None,
        sggu_code=None,
    )

    assert resolved == ("110000", "110005", "구로디지털")


def test_hospital_client_extracts_emdong_name():
    client = PublicMedicalDataClient()

    emdong_name = client._extract_emdong_name("서울 신당동")

    assert emdong_name == "신당동"


def test_region_resolution_returns_resolved_for_official_region():
    client = PublicMedicalDataClient()

    result = client.resolve_region_information("서울 구로구 신도림동")

    assert result["status"] == "resolved"
    assert result["resolved_region"]["sido_code"] == "110000"
    assert result["resolved_region"]["sggu_code"] == "110005"
    assert result["resolved_region"]["emdong_name"] == "신도림동"


def test_region_resolution_returns_unresolved_for_unofficial_alias():
    client = PublicMedicalDataClient()

    result = client.resolve_region_information("잠실")

    assert result["status"] == "unresolved"
    assert result["resolved_region"]["emdong_name"] is None
    assert result["candidates"] == []


@pytest.mark.asyncio
async def test_resolve_region_tool_uses_public_client():
    result = await resolve_region_information.ainvoke({"region_text": "서울 신당동"})

    assert result["status"] == "resolved"
    assert result["resolved_region"]["sido_code"] == "110000"
    assert result["resolved_region"]["emdong_name"] == "신당동"


def test_agent_service_strips_inline_metadata_from_content():
    service = AgentService()

    content = service._sanitize_final_content(
        "병원 안내입니다.\n\nmetadata: {\"tool\": \"search_hospital_information\"}"
    )

    assert content == "병원 안내입니다."


@pytest.mark.asyncio
async def test_hospital_client_increases_rows_for_broad_area_search(monkeypatch):
    captured = {}

    async def fake_request(self, *, base_url, endpoint, params):
        captured["params"] = params
        return {"response": {"body": {"items": {"item": []}}}}

    monkeypatch.setattr(PublicMedicalDataClient, "_request", fake_request)

    client = PublicMedicalDataClient()
    await client.search_hospitals(
        hospital_name=None,
        region_keyword="서울 신당동",
        department_name="안과",
        limit=5,
    )

    assert captured["params"]["numOfRows"] == 30


@pytest.mark.asyncio
async def test_pharmacy_client_increases_rows_for_broad_area_search(monkeypatch):
    captured = {}

    async def fake_request(self, *, base_url, endpoint, params):
        captured["params"] = params
        return {"response": {"body": {"items": {"item": []}}}}

    monkeypatch.setattr(PublicMedicalDataClient, "_request", fake_request)

    client = PublicMedicalDataClient()
    await client.search_pharmacies(
        pharmacy_name=None,
        region_keyword="서울 중랑구 신내동",
        limit=5,
    )

    assert captured["params"]["numOfRows"] == 30


def test_public_client_parses_xml_even_with_json_content_type():
    client = PublicMedicalDataClient()
    response = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        text="""<?xml version="1.0" encoding="UTF-8"?>
<response>
  <body>
    <items>
      <item>
        <itemName>타이레놀정160mg</itemName>
      </item>
    </items>
  </body>
</response>""",
    )

    parsed = client._parse_response(response)

    assert parsed["response"]["body"]["items"]["item"]["itemName"] == "타이레놀정160mg"


def test_elastic_client_maps_scalar_source_fields():
    client = ElasticDiseaseSearchClient()

    mapped = client._map_hit(
        {
            "_index": "edu-collection",
            "_id": "433765_1",
            "_score": 1.0,
            "_source": {
                "c_id": "433765_1",
                "domain": 2,
                "source": 4,
                "source_spec": "대한의학회",
                "creation_year": "2022",
                "content": "2형 당뇨병 환자는 초기부터 생활습관 교정이 필요합니다.",
            },
        }
    )

    assert mapped["c_id"] == "433765_1"
    assert mapped["domain"] == 2
    assert mapped["source"] == 4
    assert mapped["source_spec"] == "대한의학회"
    assert mapped["content"].startswith("2형 당뇨병")
