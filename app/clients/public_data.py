from __future__ import annotations

import json
from typing import Any
from xml.etree import ElementTree

import httpx

from app.core.config import settings
from app.domain.hospital_mappings import (
    DEPARTMENT_CODE_MAP,
    HOSPITAL_TYPE_CODE_MAP,
    SGGU_CODE_MAP,
    SIDO_CODE_MAP,
)


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
        items = self._extract_items(data)
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
        items = self._extract_items(data)
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
            self._parse_hospital_search_text(
                hospital_name=hospital_name,
                region_keyword=region_keyword,
                department_name=department_name,
            )
        )
        resolved_sido_code, resolved_sggu_code, parsed_region_keyword = (
            self._resolve_region_codes(
                region_keyword=parsed_region_keyword,
                sido_code=sido_code,
                sggu_code=sggu_code,
            )
        )
        resolved_emdong_name = emdong_name or self._extract_emdong_name(
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

        resolved_hospital_type_code = hospital_type_code or self._resolve_hospital_type_code(
            hospital_type_name
        )
        if resolved_hospital_type_code:
            params["clCd"] = resolved_hospital_type_code

        resolved_department_code = department_code or self._resolve_department_code(
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
        items = self._extract_items(data)
        filtered_items = self._filter_hospital_items(
            items,
            region_keyword=parsed_region_keyword,
        )
        filtered_items = self._prefer_department_name_matches(
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
        resolved_sido_code, resolved_sggu_code, parsed_region_keyword = (
            self._resolve_region_codes(
                region_keyword=region_keyword,
                sido_code=sido_code,
                sggu_code=sggu_code,
            )
        )
        resolved_emdong_name = emdong_name or self._extract_emdong_name(
            parsed_region_keyword
        )
        if resolved_emdong_name and parsed_region_keyword == resolved_emdong_name:
            parsed_region_keyword = None

        params: dict[str, Any] = {
            "pageNo": page_no,
            "numOfRows": limit,
        }
        if pharmacy_name:
            params["yadmNm"] = pharmacy_name
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
                pharmacy_name,
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
        items = self._extract_items(data)
        filtered_items = self._filter_hospital_items(
            items,
            region_keyword=parsed_region_keyword,
        )

        return {
            "query": {
                "pharmacy_name": pharmacy_name,
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
                    "post_no": item.get("postNo"),
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
            self._resolve_region_codes(
                region_keyword=normalized_text,
                sido_code=None,
                sggu_code=None,
            )
        )
        resolved_emdong_name = self._extract_emdong_name(remaining_keyword)

        candidates: list[dict[str, Any]] = []
        if resolved_sido_code:
            candidates.append(
                {
                    "region_type": "sido",
                    "name": self._find_region_name_by_code(SIDO_CODE_MAP, resolved_sido_code),
                    "code": resolved_sido_code,
                }
            )
        if resolved_sggu_code:
            candidates.append(
                {
                    "region_type": "sggu",
                    "name": self._find_region_name_by_code(SGGU_CODE_MAP, resolved_sggu_code),
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
        if not self.service_key:
            raise ValueError("PUBLIC_DATA_API_KEY is not configured.")

        request_params = {
            "serviceKey": self.service_key,
            "_type": "json",
            **params,
        }
        async with httpx.AsyncClient(
            base_url=base_url,
            timeout=self.timeout,
            follow_redirects=True,
        ) as client:
            try:
                response = await client.get(endpoint, params=request_params)
            except httpx.ConnectError as exc:
                raise ValueError(
                    "공공데이터 API 서버에 연결할 수 없습니다. 네트워크 또는 DNS 설정을 확인하세요."
                ) from exc
            if response.status_code == 401:
                raise ValueError(
                    "공공데이터 API 인증에 실패했습니다. PUBLIC_DATA_API_KEY 값을 확인하세요."
                )
            response.raise_for_status()
        return self._parse_response(response)

    def _parse_response(self, response: httpx.Response) -> dict[str, Any]:
        text = response.text.strip()
        if not text:
            return {}

        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        if text.startswith("<?xml") or text.startswith("<"):
            return self._xml_to_dict(text)

        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                pass

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise ValueError(
                "공공데이터 API 응답을 해석할 수 없습니다."
                f" content-type={content_type!r}, body_prefix={text[:120]!r}"
            )

    def _xml_to_dict(self, payload: str) -> dict[str, Any]:
        root = ElementTree.fromstring(payload)
        return {root.tag: self._xml_node_to_value(root)}

    def _xml_node_to_value(self, node: ElementTree.Element) -> Any:
        children = list(node)
        if not children:
            return (node.text or "").strip()

        grouped: dict[str, list[Any]] = {}
        for child in children:
            grouped.setdefault(child.tag, []).append(self._xml_node_to_value(child))

        return {
            key: values[0] if len(values) == 1 else values
            for key, values in grouped.items()
        }

    def _extract_items(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        response = data.get("response", data)
        body = response.get("body", {})
        items = body.get("items", {})
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            return [items]
        if isinstance(items, list):
            return items
        return []

    def _resolve_department_code(self, department_name: str | None) -> str | None:
        if not department_name:
            return None
        return DEPARTMENT_CODE_MAP.get(department_name.strip())

    def _resolve_hospital_type_code(self, hospital_type_name: str | None) -> str | None:
        if not hospital_type_name:
            return None
        return HOSPITAL_TYPE_CODE_MAP.get(hospital_type_name.strip())

    def _parse_hospital_search_text(
        self,
        *,
        hospital_name: str | None,
        region_keyword: str | None,
        department_name: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        if not hospital_name or region_keyword or department_name:
            return hospital_name, region_keyword, department_name

        normalized_name = hospital_name.strip()
        if not normalized_name:
            return None, region_keyword, department_name

        matched_department_name = None
        for candidate in sorted(DEPARTMENT_CODE_MAP.keys(), key=len, reverse=True):
            if candidate in normalized_name:
                matched_department_name = candidate
                break

        if matched_department_name is None:
            return normalized_name, region_keyword, department_name

        region_part = normalized_name.replace(matched_department_name, " ").strip()
        compact_name = normalized_name.replace(" ", "")
        parsed_hospital_name = compact_name if compact_name else normalized_name
        parsed_region_keyword = region_part or region_keyword

        return parsed_hospital_name, parsed_region_keyword, matched_department_name

    def _resolve_region_codes(
        self,
        *,
        region_keyword: str | None,
        sido_code: str | None,
        sggu_code: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        if not region_keyword:
            return sido_code, sggu_code, region_keyword

        resolved_sido_code = sido_code
        resolved_sggu_code = sggu_code
        remaining_keyword = region_keyword.strip()

        for name, code in sorted(SIDO_CODE_MAP.items(), key=lambda item: len(item[0]), reverse=True):
            if name in remaining_keyword and resolved_sido_code is None:
                resolved_sido_code = code
                remaining_keyword = remaining_keyword.replace(name, " ").strip()
                break

        for name, code in sorted(SGGU_CODE_MAP.items(), key=lambda item: len(item[0]), reverse=True):
            if name in remaining_keyword and resolved_sggu_code is None:
                resolved_sggu_code = code
                remaining_keyword = remaining_keyword.replace(name, " ").strip()
                break

        normalized_keyword = remaining_keyword if remaining_keyword else None
        return resolved_sido_code, resolved_sggu_code, normalized_keyword

    def _extract_emdong_name(self, region_keyword: str | None) -> str | None:
        if not region_keyword:
            return None

        tokens = region_keyword.split()
        for token in reversed(tokens):
            normalized = token.strip(",. ")
            if normalized.endswith(("동", "읍", "면", "리")):
                return normalized
        return None

    def _filter_hospital_items(
        self,
        items: list[dict[str, Any]],
        *,
        region_keyword: str | None,
    ) -> list[dict[str, Any]]:
        if not region_keyword:
            return items

        keyword = region_keyword.strip()
        if not keyword:
            return items

        filtered = []
        for item in items:
            address = str(item.get("addr") or "")
            hospital_name = str(item.get("yadmNm") or "")
            if keyword in address or keyword in hospital_name:
                filtered.append(item)
        return filtered

    def _prefer_department_name_matches(
        self,
        items: list[dict[str, Any]],
        *,
        department_name: str | None,
    ) -> list[dict[str, Any]]:
        if not department_name:
            return items

        exact_matches = []
        for item in items:
            hospital_name = str(item.get("yadmNm") or "")
            if department_name in hospital_name:
                exact_matches.append(item)

        return exact_matches or items

    def _find_region_name_by_code(
        self,
        mapping: dict[str, str],
        code: str | None,
    ) -> str | None:
        if code is None:
            return None
        for name, candidate_code in mapping.items():
            if candidate_code == code:
                return name
        return None
