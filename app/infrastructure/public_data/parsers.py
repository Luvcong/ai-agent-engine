from __future__ import annotations

import json
from typing import Any
from xml.etree import ElementTree

import httpx


def parse_public_data_response(response: httpx.Response) -> dict[str, Any]:
    text = response.text.strip()
    if not text:
        return {}

    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    if text.startswith("<?xml") or text.startswith("<"):
        return xml_to_dict(text)

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


def xml_to_dict(payload: str) -> dict[str, Any]:
    root = ElementTree.fromstring(payload)
    return {root.tag: xml_node_to_value(root)}


def xml_node_to_value(node: ElementTree.Element) -> Any:
    children = list(node)
    if not children:
        return (node.text or "").strip()

    grouped: dict[str, list[Any]] = {}
    for child in children:
        grouped.setdefault(child.tag, []).append(xml_node_to_value(child))

    return {
        key: values[0] if len(values) == 1 else values
        for key, values in grouped.items()
    }


def extract_items(data: dict[str, Any]) -> list[dict[str, Any]]:
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
