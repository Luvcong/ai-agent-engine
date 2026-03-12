from __future__ import annotations

from typing import Any

from app.domain.hospital_mappings import DEPARTMENT_CODE_MAP, HOSPITAL_TYPE_CODE_MAP


def resolve_department_code(department_name: str | None) -> str | None:
    if not department_name:
        return None
    return DEPARTMENT_CODE_MAP.get(department_name.strip())


def resolve_hospital_type_code(hospital_type_name: str | None) -> str | None:
    if not hospital_type_name:
        return None
    return HOSPITAL_TYPE_CODE_MAP.get(hospital_type_name.strip())


def parse_hospital_search_text(
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


def filter_hospital_items(
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


def prefer_department_name_matches(
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
