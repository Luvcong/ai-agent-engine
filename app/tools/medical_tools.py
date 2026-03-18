from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.clients.elasticsearch import ElasticDiseaseSearchClient
from app.clients.public_data import PublicMedicalDataClient
from app.core.config import settings


def _tool_error_response(
    *,
    tool_name: str,
    query: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "query": query,
        "count": 0,
        "items": [],
        "error": error,
    }


# TODO: 추후 규칙 기반 정렬 또는 리랭킹 로직 적용 필요 - 현재 단순 슬라이싱
def _truncate_items(items: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return items[:limit]


@tool
async def search_drug_info(
    item_name: str,
    enterprise_name: str | None = None,
    limit: int = settings.DRUG_SEARCH_LIMIT,
) -> dict[str, Any]:
    """의약품명으로 의약품개요정보(e약은요) API를 조회하여 효능, 사용법, 주의사항, 부작용, 보관법 등을 조회합니다."""
    client = PublicMedicalDataClient()
    try:
        result = await client.search_drugs(
            item_name=item_name,
            enterprise_name=enterprise_name,
            limit=limit,
        )
    except ValueError as exc:
        return _tool_error_response(
            tool_name="search_drug_info",
            query={"item_name": item_name, "enterprise_name": enterprise_name},
            error=str(exc),
        )
    result["items"] = _truncate_items(result["items"], limit)
    return result


@tool
async def search_disease_info(
    disease_name: str,
    limit: int = settings.DISEASE_SEARCH_LIMIT,
) -> dict[str, Any]:
    """질병명으로 질병명칭/코드 정보를 조회합니다."""
    client = PublicMedicalDataClient()
    try:
        result = await client.search_diseases(
            query=disease_name,
            limit=limit,
        )
    except ValueError as exc:
        return _tool_error_response(
            tool_name="search_disease_info",
            query={"disease_name": disease_name},
            error=str(exc),
        )
    result["items"] = _truncate_items(result["items"], limit)
    return result


@tool
async def search_disease_knowledge(
    query: str,
    domain: int | None = None,
    source: int | None = None,
    source_spec: str | None = None,
    creation_year: str | None = None,
    limit: int = settings.ELASTICSEARCH_DISEASE_SEARCH_LIMIT,
) -> dict[str, Any]:
    """Elasticsearch의 edu-collection에서 질병 설명, 치료 원칙, 관리법, 가이드라인을 조회합니다."""
    client = ElasticDiseaseSearchClient()
    result = await client.search_disease_knowledge(
        query=query,
        domain=domain,
        source=source,
        source_spec=source_spec,
        creation_year=creation_year,
        limit=limit,
    )
    result["items"] = _truncate_items(result["items"], limit)
    return result


@tool
async def search_hospital_info(
    hospital_name: str | None = None,
    region_keyword: str | None = None,
    sido_code: str | None = None,
    sggu_code: str | None = None,
    emdong_name: str | None = None,
    hospital_type_name: str | None = None,
    hospital_type_code: str | None = None,
    department_name: str | None = None,
    department_code: str | None = None,
    x_pos: str | float | None = None,
    y_pos: str | float | None = None,
    radius: str | int | None = None,
    limit: int = settings.HOSPITAL_SEARCH_LIMIT,
) -> dict[str, Any]:
    """병원명, 지역, 종별, 진료과, 좌표 반경 조건으로 병원 기본 정보를 조회합니다."""
    client = PublicMedicalDataClient()
    query = {
        "hospital_name": hospital_name,
        "region_keyword": region_keyword,
        "sido_code": sido_code,
        "sggu_code": sggu_code,
        "emdong_name": emdong_name,
        "hospital_type_name": hospital_type_name,
        "hospital_type_code": hospital_type_code,
        "department_name": department_name,
        "department_code": department_code,
        "x_pos": x_pos,
        "y_pos": y_pos,
        "radius": radius,
    }
    try:
        result = await client.search_hospitals(
            hospital_name=hospital_name,
            region_keyword=region_keyword,
            sido_code=sido_code,
            sggu_code=sggu_code,
            emdong_name=emdong_name,
            hospital_type_name=hospital_type_name,
            hospital_type_code=hospital_type_code,
            department_name=department_name,
            department_code=department_code,
            x_pos=x_pos,
            y_pos=y_pos,
            radius=radius,
            limit=limit,
        )
    except ValueError as exc:
        return _tool_error_response(
            tool_name="search_hospital_info",
            query=query,
            error=str(exc),
        )
    result["items"] = _truncate_items(result["items"], limit)
    return result


@tool
async def search_pharmacy_info(
    pharmacy_name: str | None = None,
    region_keyword: str | None = None,
    sido_code: str | None = None,
    sggu_code: str | None = None,
    emdong_name: str | None = None,
    x_pos: str | float | None = None,
    y_pos: str | float | None = None,
    radius: str | int | None = None,
    limit: int = settings.PHARMACY_SEARCH_LIMIT,
) -> dict[str, Any]:
    """약국명, 지역, 좌표 반경 조건으로 약국 기본 정보를 조회합니다."""
    client = PublicMedicalDataClient()
    query = {
        "pharmacy_name": pharmacy_name,
        "region_keyword": region_keyword,
        "sido_code": sido_code,
        "sggu_code": sggu_code,
        "emdong_name": emdong_name,
        "x_pos": x_pos,
        "y_pos": y_pos,
        "radius": radius,
    }
    try:
        result = await client.search_pharmacies(
            pharmacy_name=pharmacy_name,
            region_keyword=region_keyword,
            sido_code=sido_code,
            sggu_code=sggu_code,
            emdong_name=emdong_name,
            x_pos=x_pos,
            y_pos=y_pos,
            radius=radius,
            limit=limit,
        )
    except ValueError as exc:
        return _tool_error_response(
            tool_name="search_pharmacy_info",
            query=query,
            error=str(exc),
        )
    result["items"] = _truncate_items(result["items"], limit)
    return result


@tool
async def resolve_region_information(region_text: str) -> dict[str, Any]:
    """사용자가 말한 지역명을 시도/시군구/읍면동 기준으로 해석하고, 애매하면 재질문이 필요한지 판단합니다."""
    client = PublicMedicalDataClient()
    return client.resolve_region_information(region_text=region_text)
