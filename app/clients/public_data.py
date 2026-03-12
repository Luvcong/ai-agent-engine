from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.domain.hospital_search import (
    filter_hospital_items,
    parse_hospital_search_text,
    prefer_department_name_matches,
    resolve_department_code,
    resolve_hospital_type_code,
)
from app.domain.hospital_mappings import (
    SGGU_CODE_MAP,
    SIDO_CODE_MAP,
)
from app.domain.region_resolution import (
    extract_emdong_name,
    find_region_name_by_code,
    resolve_region_codes,
)
from app.infrastructure.public_data.parsers import extract_items, parse_public_data_response
from app.infrastructure.public_data.transport import request_public_data


class PublicMedicalDataClient:
    DRUG_BASE_URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService"
    DISEASE_BASE_URL = "https://apis.data.go.kr/B551182/diseaseInfoService1"
    HOSPITAL_BASE_URL = "https://apis.data.go.kr/B551182/hospInfoServicev2"
    PHARMACY_BASE_URL = "https://apis.data.go.kr/B551182/pharmacyInfoService"

    def __init__(self) -> None:
        self.service_key = settings.PUBLIC_DATA_API_KEY
        self.timeout = settings.PUBLIC_DATA_TIMEOUT

    async def search_drugs(
        self,
        *,
        item_name: str,
        enterprise_name: str | None = None,
        page_no: int = 1,
        limit: int = 5,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "itemName": item_name,
            "pageNo": page_no,
            "numOfRows": limit,
        }
        if enterprise_name:
            params["entpName"] = enterprise_name

        data = await self._request(
            base_url=self.DRUG_BASE_URL,
            endpoint="/getDrbEasyDrugList",
            params=params,
        )
        items = extract_items(data)
        return {
            "query": {"item_name": item_name, "enterprise_name": enterprise_name},
            "count": len(items),
            "items": [
                {
                    "item_name": item.get("itemName"),
                    "enterprise_name": item.get("entpName"),
                    "ingredient": item.get("mainItemIngr"),
                    "efficacy": item.get("efcyQesitm"),
                    "usage": item.get("useMethodQesitm"),
                    "warning": item.get("atpnWarnQesitm"),
                    "precaution": item.get("atpnQesitm"),
                    "interaction": item.get("intrcQesitm"),
                    "side_effect": item.get("seQesitm"),
                    "storage": item.get("depositMethodQesitm"),
                }
                for item in items
            ],
        }

    async def search_diseases(
        self,
        *,
        query: str,
        page_no: int = 1,
        limit: int = 5,
        sickness_type: str = "1",
        medical_type: str = "1",
    ) -> dict[str, Any]:
        data = await self._request(
            base_url=self.DISEASE_BASE_URL,
            endpoint="/getDissNameCodeList1",
            params={
                "sickType": sickness_type,
                "medTp": medical_type,
                "diseaseType": "SICK_NM",
                "searchText": query,
                "pageNo": page_no,
                "numOfRows": limit,
            },
        )
        items = extract_items(data)
        return {
            "query": {"disease_name": query},
            "count": len(items),
            "items": [
                {
                    "disease_code": item.get("sickCd"),
                    "disease_name": item.get("sickNm"),
                    "similar_name": item.get("sickNmEng"),
                }
                for item in items
            ],
        }

    async def search_hospitals(
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
        page_no: int = 1,
        limit: int = 5,
    ) -> dict[str, Any]:
        parsed_hospital_name, parsed_region_keyword, parsed_department_name = (
            parse_hospital_search_text(
                hospital_name=hospital_name,
                region_keyword=region_keyword,
                department_name=department_name,
            )
        )
        resolved_sido_code, resolved_sggu_code, parsed_region_keyword = (
            resolve_region_codes(
                region_keyword=parsed_region_keyword,
                sido_code=sido_code,
                sggu_code=sggu_code,
            )
        )
        resolved_emdong_name = emdong_name or extract_emdong_name(
            parsed_region_keyword
        )
        if resolved_emdong_name and parsed_region_keyword == resolved_emdong_name:
            parsed_region_keyword = None

        params: dict[str, Any] = {
            "pageNo": page_no,
            "numOfRows": limit,
        }
        if parsed_hospital_name:
            params["yadmNm"] = parsed_hospital_name
        if resolved_sido_code:
            params["sidoCd"] = resolved_sido_code
        if resolved_sggu_code:
            params["sgguCd"] = resolved_sggu_code
        if resolved_emdong_name:
            params["emdongNm"] = resolved_emdong_name

        resolved_hospital_type_code = hospital_type_code or resolve_hospital_type_code(
            hospital_type_name
        )
        if resolved_hospital_type_code:
            params["clCd"] = resolved_hospital_type_code

        resolved_department_code = department_code or resolve_department_code(
            parsed_department_name
        )
        if resolved_department_code:
            params["dgsbjtCd"] = resolved_department_code

        if x_pos is not None:
            params["xPos"] = str(x_pos)
        if y_pos is not None:
            params["yPos"] = str(y_pos)
        if radius is not None:
            params["radius"] = str(radius)

        if not any(
            [
                parsed_hospital_name,
                parsed_region_keyword,
                resolved_sido_code,
                resolved_sggu_code,
                resolved_emdong_name,
                resolved_hospital_type_code,
                parsed_department_name,
                department_code,
                x_pos,
                y_pos,
                radius,
            ]
        ):
            raise ValueError("병원 검색에는 최소 1개 이상의 검색 조건이 필요합니다.")

        if (
            "yadmNm" not in params
            and any(key in params for key in ("dgsbjtCd", "clCd", "emdongNm", "sidoCd", "sgguCd"))
            and params["numOfRows"] < 30
        ):
            params["numOfRows"] = 30

        data = await self._request(
            base_url=self.HOSPITAL_BASE_URL,
            endpoint="/getHospBasisList",
            params=params,
        )
        items = extract_items(data)
        filtered_items = filter_hospital_items(
            items,
            region_keyword=parsed_region_keyword,
        )
        filtered_items = prefer_department_name_matches(
            filtered_items,
            department_name=parsed_department_name,
        )
        return {
            "query": {
                "hospital_name": parsed_hospital_name,
                "region_keyword": parsed_region_keyword,
                "sido_code": resolved_sido_code,
                "sggu_code": resolved_sggu_code,
                "emdong_name": resolved_emdong_name,
                "hospital_type_name": hospital_type_name,
                "hospital_type_code": resolved_hospital_type_code,
                "department_name": parsed_department_name,
                "department_code": resolved_department_code,
                "x_pos": str(x_pos) if x_pos is not None else None,
                "y_pos": str(y_pos) if y_pos is not None else None,
                "radius": str(radius) if radius is not None else None,
            },
            "count": len(filtered_items),
            "items": [
                {
                    "hospital_name": item.get("yadmNm"),
                    "hospital_type": item.get("clCdNm"),
                    "sido_name": item.get("sidoCdNm"),
                    "sggu_name": item.get("sgguCdNm"),
                    "emdong_name": item.get("emdongNm"),
                    "address": item.get("addr"),
                    "telephone": item.get("telno"),
                    "homepage": item.get("hospUrl"),
                    "establishment_date": item.get("estbDd"),
                    "x_pos": item.get("XPos"),
                    "y_pos": item.get("YPos"),
                }
                for item in filtered_items
            ],
        }

    async def search_pharmacies(
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
        page_no: int = 1,
        limit: int = 5,
    ) -> dict[str, Any]:
        normalized_pharmacy_name = pharmacy_name.strip() if pharmacy_name else None
        if normalized_pharmacy_name == "":
            normalized_pharmacy_name = None

        resolved_sido_code, resolved_sggu_code, parsed_region_keyword = (
            resolve_region_codes(
                region_keyword=region_keyword,
                sido_code=sido_code,
                sggu_code=sggu_code,
            )
        )
        resolved_emdong_name = emdong_name or extract_emdong_name(parsed_region_keyword)
        if resolved_emdong_name and parsed_region_keyword == resolved_emdong_name:
            parsed_region_keyword = None

        params: dict[str, Any] = {
            "pageNo": page_no,
            "numOfRows": limit,
        }
        if normalized_pharmacy_name:
            params["yadmNm"] = normalized_pharmacy_name
        if resolved_sido_code:
            params["sidoCd"] = resolved_sido_code
        if resolved_sggu_code:
            params["sgguCd"] = resolved_sggu_code
        if resolved_emdong_name:
            params["emdongNm"] = resolved_emdong_name
        if x_pos is not None:
            params["xPos"] = str(x_pos)
        if y_pos is not None:
            params["yPos"] = str(y_pos)
        if radius is not None:
            params["radius"] = str(radius)

        if not any(
            [
                normalized_pharmacy_name,
                parsed_region_keyword,
                resolved_sido_code,
                resolved_sggu_code,
                resolved_emdong_name,
                x_pos,
                y_pos,
                radius,
            ]
        ):
            raise ValueError("약국 검색에는 최소 1개 이상의 검색 조건이 필요합니다.")

        if (
            "yadmNm" not in params
            and any(key in params for key in ("emdongNm", "sidoCd", "sgguCd"))
            and params["numOfRows"] < 30
        ):
            params["numOfRows"] = 30

        data = await self._request(
            base_url=self.PHARMACY_BASE_URL,
            endpoint="/getParmacyBasisList",
            params=params,
        )
        items = extract_items(data)
        filtered_items = filter_hospital_items(items, region_keyword=parsed_region_keyword)

        return {
            "query": {
                "pharmacy_name": normalized_pharmacy_name,
                "region_keyword": parsed_region_keyword,
                "sido_code": resolved_sido_code,
                "sggu_code": resolved_sggu_code,
                "emdong_name": resolved_emdong_name,
                "x_pos": str(x_pos) if x_pos is not None else None,
                "y_pos": str(y_pos) if y_pos is not None else None,
                "radius": str(radius) if radius is not None else None,
            },
            "count": len(filtered_items),
            "items": [
                {
                    "pharmacy_name": item.get("yadmNm"),
                    "sido_name": item.get("sidoCdNm"),
                    "sggu_name": item.get("sgguCdNm"),
                    "emdong_name": item.get("emdongNm"),
                    "address": item.get("addr"),
                    "telephone": item.get("telno"),
                    "homepage": item.get("hospUrl"),
                    "x_pos": item.get("XPos"),
                    "y_pos": item.get("YPos"),
                }
                for item in filtered_items
            ],
        }

    def resolve_region_information(self, region_text: str) -> dict[str, Any]:
        normalized_text = region_text.strip()
        if not normalized_text:
            raise ValueError("지역명은 비워둘 수 없습니다.")

        resolved_sido_code, resolved_sggu_code, remaining_keyword = (
            resolve_region_codes(
                region_keyword=normalized_text,
                sido_code=None,
                sggu_code=None,
            )
        )
        resolved_emdong_name = extract_emdong_name(remaining_keyword)

        candidates: list[dict[str, Any]] = []
        if resolved_sido_code:
            candidates.append(
                {
                    "region_type": "sido",
                    "name": find_region_name_by_code(SIDO_CODE_MAP, resolved_sido_code),
                    "code": resolved_sido_code,
                }
            )
        if resolved_sggu_code:
            candidates.append(
                {
                    "region_type": "sggu",
                    "name": find_region_name_by_code(SGGU_CODE_MAP, resolved_sggu_code),
                    "code": resolved_sggu_code,
                }
            )
        if resolved_emdong_name:
            candidates.append(
                {
                    "region_type": "emdong",
                    "name": resolved_emdong_name,
                    "code": None,
                }
            )

        if candidates:
            return {
                "query": {"region_text": normalized_text},
                "status": "resolved",
                "resolved_region": {
                    "sido_code": resolved_sido_code,
                    "sggu_code": resolved_sggu_code,
                    "emdong_name": resolved_emdong_name,
                    "remaining_keyword": (
                        remaining_keyword if remaining_keyword != resolved_emdong_name else None
                    ),
                },
                "candidates": candidates,
                "aliases": [],
            }

        return {
            "query": {"region_text": normalized_text},
            "status": "unresolved",
            "resolved_region": {
                "sido_code": None,
                "sggu_code": None,
                "emdong_name": None,
                "remaining_keyword": normalized_text,
            },
            "candidates": [],
            "aliases": [],
        }

    async def _request(
        self,
        *,
        base_url: str,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        return await request_public_data(
            base_url=base_url,
            endpoint=endpoint,
            params=params,
            service_key=self.service_key,
            timeout=self.timeout,
        )

    def _parse_response(self, response) -> dict[str, Any]:
        return parse_public_data_response(response)
