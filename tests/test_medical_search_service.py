import pytest

from app.clients.public_data import PublicMedicalDataClient
from app.core.config import settings
from app.services.medical_search_service import MedicalSearchService


@pytest.mark.asyncio
async def test_medical_search_service_applies_default_drug_limit(monkeypatch):
    captured = {}

    async def fake_search_drugs(self, **kwargs):
        captured.update(kwargs)
        return {
            "query": kwargs,
            "count": 3,
            "items": [
                {"item_name": "A"},
                {"item_name": "B"},
                {"item_name": "C"},
            ],
        }

    monkeypatch.setattr(PublicMedicalDataClient, "search_drugs", fake_search_drugs)

    service = MedicalSearchService()
    result = await service.search_drug_info(item_name="타이레놀", limit=None)

    assert captured["limit"] == settings.DRUG_SEARCH_LIMIT
    assert len(result["items"]) == min(3, settings.DRUG_SEARCH_LIMIT)


@pytest.mark.asyncio
async def test_medical_search_service_truncates_drug_items_to_explicit_limit(monkeypatch):
    async def fake_search_drugs(self, **kwargs):
        return {
            "query": kwargs,
            "count": 3,
            "items": [
                {"item_name": "A"},
                {"item_name": "B"},
                {"item_name": "C"},
            ],
        }

    monkeypatch.setattr(PublicMedicalDataClient, "search_drugs", fake_search_drugs)

    service = MedicalSearchService()
    result = await service.search_drug_info(item_name="타이레놀", limit=2)

    assert [item["item_name"] for item in result["items"]] == ["A", "B"]


@pytest.mark.asyncio
async def test_medical_search_service_applies_default_disease_limit(monkeypatch):
    captured = {}

    async def fake_search_diseases(self, **kwargs):
        captured.update(kwargs)
        return {
            "query": kwargs,
            "count": 2,
            "items": [
                {"disease_code": "A"},
                {"disease_code": "B"},
            ],
        }

    monkeypatch.setattr(PublicMedicalDataClient, "search_diseases", fake_search_diseases)

    service = MedicalSearchService()
    result = await service.search_disease_info(disease_name="감기", limit=None)

    assert captured["limit"] == settings.DISEASE_SEARCH_LIMIT
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_medical_search_service_applies_default_hospital_limit(monkeypatch):
    captured = {}

    async def fake_search_hospitals(self, **kwargs):
        captured.update(kwargs)
        return {
            "query": kwargs,
            "count": 3,
            "items": [
                {"hospital_name": "A"},
                {"hospital_name": "B"},
                {"hospital_name": "C"},
            ],
        }

    monkeypatch.setattr(PublicMedicalDataClient, "search_hospitals", fake_search_hospitals)

    service = MedicalSearchService()
    result = await service.search_hospital_info(region_keyword="서울", limit=None)

    assert captured["limit"] == settings.HOSPITAL_SEARCH_LIMIT
    assert len(result["items"]) == min(3, settings.HOSPITAL_SEARCH_LIMIT)


@pytest.mark.asyncio
async def test_medical_search_service_applies_default_pharmacy_limit(monkeypatch):
    captured = {}

    async def fake_search_pharmacies(self, **kwargs):
        captured.update(kwargs)
        return {
            "query": kwargs,
            "count": 2,
            "items": [
                {"pharmacy_name": "A"},
                {"pharmacy_name": "B"},
            ],
        }

    monkeypatch.setattr(PublicMedicalDataClient, "search_pharmacies", fake_search_pharmacies)

    service = MedicalSearchService()
    result = await service.search_pharmacy_info(region_keyword="서울", limit=None)

    assert captured["limit"] == settings.HOSPITAL_SEARCH_LIMIT
    assert len(result["items"]) == 2


@pytest.mark.asyncio
async def test_medical_search_service_resolve_region_information_passthrough(monkeypatch):
    async def not_used(*args, **kwargs):
        raise AssertionError("unexpected async path")

    def fake_resolve_region_information(self, *, region_text: str):
        return {
            "query": {"region_text": region_text},
            "status": "resolved",
            "resolved_region": {
                "sido_code": "110000",
                "sggu_code": None,
                "emdong_name": "신당동",
                "remaining_keyword": None,
            },
            "candidates": [],
            "aliases": [],
        }

    monkeypatch.setattr(PublicMedicalDataClient, "resolve_region_information", fake_resolve_region_information)
    monkeypatch.setattr(PublicMedicalDataClient, "search_drugs", not_used)

    service = MedicalSearchService()
    result = await service.resolve_region_information(region_text="서울 신당동")

    assert result["status"] == "resolved"
    assert result["resolved_region"]["emdong_name"] == "신당동"
