from __future__ import annotations

from app.domain.hospital_mappings import SGGU_CODE_MAP, SIDO_CODE_MAP


def resolve_region_codes(
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


def extract_emdong_name(region_keyword: str | None) -> str | None:
    if not region_keyword:
        return None

    tokens = region_keyword.split()
    for token in reversed(tokens):
        normalized = token.strip(",. ")
        if normalized.endswith(("동", "읍", "면", "리")):
            return normalized
    return None


def find_region_name_by_code(
    mapping: dict[str, str],
    code: str | None,
) -> str | None:
    if code is None:
        return None
    for name, candidate_code in mapping.items():
        if candidate_code == code:
            return name
    return None
