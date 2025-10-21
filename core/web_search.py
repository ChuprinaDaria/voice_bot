from __future__ import annotations

import json
import re
from typing import Dict, Any, List


def web_search(query: str, language: str = "uk", max_results: int = 3) -> str:
    if language == "uk":
        return f"Результати пошуку для '{query}' будуть доступні після реалізації інтеграції з пошуковим API."
    if language == "de":
        return f"Suchergebnisse für '{query}' werden nach der Implementierung der Such-API-Integration verfügbar sein."
    return f"Search results for '{query}' will be available after implementing search API integration."


def extract_relevant_info(query: str, results: List[Dict[str, Any]]) -> str:
    summary = "Ось що я знайшов за вашим запитом: ..."
    return summary
