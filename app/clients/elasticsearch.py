from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class ElasticDiseaseSearchClient:
    # Elasticsearch 접속에 필요한 설정값을 로드한다.
    def __init__(self) -> None:
        self.base_url = settings.ELASTICSEARCH_URL
        self.index_name = settings.ELASTICSEARCH_INDEX
        self.username = settings.ELASTICSEARCH_USERNAME
        self.password = settings.ELASTICSEARCH_PASSWORD
        self.timeout = settings.ELASTICSEARCH_TIMEOUT

    # 질병 관련 지식을 Elasticsearch에서 검색해 요약된 문서 목록으로 반환한다.
    async def search_disease_knowledge(
        self,
        *,
        query: str,
        limit: int = 5,
        domain: int | None = None,
        source: int | None = None,
        source_spec: str | None = None,
        creation_year: str | None = None,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("질의어는 비워둘 수 없습니다.")
        if not self.base_url:
            raise ValueError("ELASTICSEARCH_URL is not configured.")
        if not self.index_name:
            raise ValueError("ELASTICSEARCH_INDEX is not configured.")

        filters: list[dict[str, Any]] = []
        if domain is not None:
            filters.append({"term": {"domain": domain}})
        if source is not None:
            filters.append({"term": {"source": source}})
        if source_spec:
            filters.append({"match_phrase": {"source_spec": source_spec}})
        if creation_year:
            filters.append({"match_phrase": {"creation_year": creation_year}})

        payload = {
            "size": limit,
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": normalized_query,
                                "fields": ["content^3", "source_spec^2", "c_id"],
                                "type": "best_fields",
                            }
                        }
                    ],
                    "filter": filters,
                }
            },
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 280,
                        "number_of_fragments": 1,
                    }
                }
            },
        }

        try:
            async with httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                timeout=self.timeout,
                auth=(self.username, self.password),
                follow_redirects=True,
            ) as client:
                response = await client.post(f"/{self.index_name}/_search", json=payload)
                if response.status_code == 401:
                    raise ValueError(
                        "Elasticsearch 인증에 실패했습니다. 계정 정보 설정을 확인하세요."
                    )
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ValueError(
                "Elasticsearch 서버에 연결할 수 없습니다. 네트워크 또는 DNS 설정을 확인하세요."
            ) from exc
        except httpx.ReadTimeout as exc:
            raise ValueError(
                "Elasticsearch 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요."
            ) from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip()
            if len(detail) > 300:
                detail = f"{detail[:300]}..."
            if exc.response.status_code == 400:
                raise ValueError(
                    f"Elasticsearch 검색 요청이 잘못되었습니다. query={normalized_query!r}, "
                    f"status=400, detail={detail or 'empty response body'}"
                ) from exc
            raise ValueError(
                f"Elasticsearch 검색 중 오류가 발생했습니다. "
                f"status={exc.response.status_code}, detail={detail or 'empty response body'}"
            ) from exc

        data = response.json()
        hits = data.get("hits", {}).get("hits", [])

        return {
            "query": {
                "text": normalized_query,
                "domain": domain,
                "source": source,
                "source_spec": source_spec,
                "creation_year": creation_year,
            },
            "count": len(hits),
            "items": [self._map_hit(hit) for hit in hits],
        }

    # Elasticsearch hit 한 건을 API 응답용 필드 구조로 정규화한다.
    def _map_hit(self, hit: dict[str, Any]) -> dict[str, Any]:
        source = hit.get("_source", {})
        highlight = hit.get("highlight", {})
        content = self._normalize_scalar(source.get("content"))
        excerpt = self._normalize_highlight(highlight.get("content")) or content

        return {
            "document_id": hit.get("_id"),
            "collection": hit.get("_index"),
            "score": hit.get("_score"),
            "c_id": self._normalize_scalar(source.get("c_id")),
            "domain": self._normalize_scalar(source.get("domain")),
            "source": self._normalize_scalar(source.get("source")),
            "source_spec": self._normalize_scalar(source.get("source_spec")),
            "creation_year": self._normalize_scalar(source.get("creation_year")),
            "excerpt": excerpt,
            "content": content,
        }

    # 배열로 들어온 단일값 필드를 스칼라 값으로 평탄화한다.
    def _normalize_scalar(self, value: Any) -> Any:
        if isinstance(value, list):
            return value[0] if value else None
        return value

    # highlight 필드를 문자열로 정규화해 없으면 None을 반환한다.
    def _normalize_highlight(self, value: Any) -> str | None:
        normalized = self._normalize_scalar(value)
        if normalized is None:
            return None
        return str(normalized)
