from __future__ import annotations

from langchain_core.tools import tool

from app.services.medical_search_service import medical_search_service

@tool
async def search_drug_info(
    item_name: str,
    enterprise_name: str | None = None,
    limit: int | None = None,
) -> dict:
    """의약품명으로 의약품개요정보(e약은요) API를 조회하여 효능, 사용법, 주의사항, 부작용, 보관법 등을 조회합니다."""
    result = await medical_search_service.search_drug_info(
        item_name=item_name,
        enterprise_name=enterprise_name,
        limit=limit,
    )
    return result


@tool
async def search_disease_info(
    disease_name: str,
    limit: int | None = None,
) -> dict:
    """질병명으로 질병명칭/코드 정보를 조회합니다."""
    result = await medical_search_service.search_disease_info(
        disease_name=disease_name,
        limit=limit,
    )
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
    limit: int | None = None,
) -> dict:
    """병원명, 지역, 종별, 진료과, 좌표 반경 조건으로 병원 기본 정보를 조회합니다."""
    result = await medical_search_service.search_hospital_info(
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
    limit: int | None = None,
) -> dict:
    """약국명, 지역, 좌표 반경 조건으로 약국 기본 정보를 조회합니다."""
    result = await medical_search_service.search_pharmacy_info(
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
    return result


@tool
async def resolve_region_information(region_text: str) -> dict:
    """사용자가 말한 지역명을 시도/시군구/읍면동 기준으로 해석하고, 애매하면 재질문이 필요한지 판단합니다."""
    return await medical_search_service.resolve_region_information(
        region_text=region_text
    )
