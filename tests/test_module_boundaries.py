from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

ACTIVE_RUNTIME_FILES = [
    "app/main.py",
    "app/api/routes/chat.py",
    "app/api/routes/threads.py",
    "app/services/agent_service.py",
    "app/services/medical_search_service.py",
    "app/services/threads_service.py",
    "app/agents/medical.py",
    "app/prompt.py",
    "app/tools/medical_tools.py",
    "app/clients/public_data.py",
    "app/core/config.py",
    "app/domain/hospital_mappings.py",
    "app/domain/hospital_search.py",
    "app/domain/region_resolution.py",
    "app/infrastructure/public_data/parsers.py",
    "app/infrastructure/public_data/transport.py",
    "app/orchestration/streaming.py",
    "app/schemas/chat.py",
    "app/schemas/threads.py",
    "app/schemas/agent_response.py",
    "app/utils/logger.py",
    "app/utils/read_json.py",
]


def iter_imports(file_path: Path) -> set[str]:
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def test_active_runtime_does_not_import_legacy_service_modules():
    forbidden_modules = {
        "app.services.conversation_service",
    }

    for relative_path in ACTIVE_RUNTIME_FILES:
        imports = iter_imports(REPO_ROOT / relative_path)
        assert imports.isdisjoint(forbidden_modules), relative_path


def test_active_runtime_does_not_import_legacy_models_package_root():
    for relative_path in ACTIVE_RUNTIME_FILES:
        imports = iter_imports(REPO_ROOT / relative_path)
        assert "app.models" not in imports, relative_path


def test_active_runtime_does_not_depend_on_langchain_test_examples():
    for relative_path in ACTIVE_RUNTIME_FILES:
        imports = iter_imports(REPO_ROOT / relative_path)
        assert all(not module.startswith("langchain_test") for module in imports), relative_path
