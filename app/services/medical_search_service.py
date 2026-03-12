from __future__ import annotations

from typing import Any

from app.clients.public_data import PublicMedicalDataClient
from app.core.config import settings


class MedicalSearchService:
    def __init__(
        self,
        client: PublicMedicalDataClient | None = None,
    ) -> None:
        self.client = client or PublicMedicalDataClient()

    async def search_drug_info(
        self,
        *,
        item_name: str,
        enterprise_name: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        effective_limit = limit or settings.DRUG_SEARCH_LIMIT
        result = await self.client.search_drugs(
            item_name=item_name,
            enterprise_name=enterprise_name,
            limit=effective_limit,
        )
        result["items"] = result["items"][:effective_limit]
        return result

    async def search_disease_info(
        self,
        *,
        disease_name: str,
        limit: int | None = None,
    ) -> dict[str, Any]:
        effective_limit = limit or settings.DISEASE_SEARCH_LIMIT
        result = await self.client.search_diseases(
            query=disease_name,
            limit=effective_limit,
        )
        result["items"] = result["items"][:effective_limit]
        return result

    async def search_hospital_info(
        self,
        *,
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
    ) -> dict[str, Any]:
        effective_limit = limit or settings.HOSPITAL_SEARCH_LIMIT
        result = await self.client.search_hospitals(
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
            limit=effective_limit,
        )
        result["items"] = result["items"][:effective_limit]
        return result

    async def search_pharmacy_info(
        self,
        *,
        pharmacy_name: str | None = None,
        region_keyword: str | None = None,
        sido_code: str | None = None,
        sggu_code: str | None = None,
        emdong_name: str | None = None,
        x_pos: str | float | None = None,
        y_pos: str | float | None = None,
        radius: str | int | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        effective_limit = limit or settings.HOSPITAL_SEARCH_LIMIT
        result = await self.client.search_pharmacies(
            pharmacy_name=pharmacy_name,
            region_keyword=region_keyword,
            sido_code=sido_code,
            sggu_code=sggu_code,
            emdong_name=emdong_name,
            x_pos=x_pos,
            y_pos=y_pos,
            radius=radius,
            limit=effective_limit,
        )
        result["items"] = result["items"][:effective_limit]
        return result

    async def resolve_region_information(
        self,
        *,
        region_text: str,
    ) -> dict[str, Any]:
        return self.client.resolve_region_information(region_text=region_text)


medical_search_service = MedicalSearchService()
