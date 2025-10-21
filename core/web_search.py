from __future__ import annotations

import json
import re
from typing import Dict, Any, List, Optional
import httpx
from bs4 import BeautifulSoup  # type: ignore[import-not-found]


def web_search(query: str, language: str = "uk", max_results: int = 3) -> str:
    """
    Виконує веб-пошук через DuckDuckGo HTML (без API ключа)
    
    Args:
        query: Пошуковий запит
        language: Мова інтерфейсу (uk, en, de)
        max_results: Максимальна кількість результатів
    
    Returns:
        Короткий саммарі результатів пошуку
    """
    try:
        # DuckDuckGo HTML пошук (не потребує API ключа)
        results = _search_duckduckgo(query, max_results)
        
        if not results:
            if language == "uk":
                return f"На жаль, не вдалося знайти результати для '{query}'."
            elif language == "de":
                return f"Leider konnten keine Ergebnisse für '{query}' gefunden werden."
            else:
                return f"Sorry, couldn't find results for '{query}'."
        
        # Формуємо короткий саммарі
        summary = _format_search_results(results, query, language)
        return summary
        
    except Exception as e:
        print(f"❌ Помилка веб-пошуку: {e}")
        if language == "uk":
            return f"Вибачте, виникла помилка при пошуку інформації про '{query}'."
        elif language == "de":
            return f"Entschuldigung, es gab einen Fehler bei der Suche nach Informationen über '{query}'."
        else:
            return f"Sorry, there was an error searching for information about '{query}'."


def _search_duckduckgo(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Пошук через DuckDuckGo HTML (без API)
    
    Returns:
        Список словників з 'title', 'snippet', 'url'
    """
    try:
        # DuckDuckGo HTML search
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        data = {"q": query}
        
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.post(url, headers=headers, data=data)
            response.raise_for_status()
        
        # Парсимо HTML
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        # Знаходимо результати пошуку
        for result_div in soup.find_all("div", class_="result", limit=max_results):
            try:
                # Витягуємо заголовок
                title_tag = result_div.find("a", class_="result__a")
                title = title_tag.get_text(strip=True) if title_tag else ""
                
                # Витягуємо URL
                url_link = title_tag.get("href", "") if title_tag else ""
                
                # Витягуємо snippet (опис)
                snippet_tag = result_div.find("a", class_="result__snippet")
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
                
                if title and snippet:
                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "url": url_link
                    })
            except Exception:
                continue
        
        return results
        
    except Exception as e:
        print(f"⚠️  Помилка DuckDuckGo пошуку: {e}")
        return []


def _format_search_results(results: List[Dict[str, str]], query: str, language: str) -> str:
    """
    Форматує результати пошуку в коротку відповідь
    """
    if not results:
        return ""
    
    # Беремо перші 2-3 результати для короткої відповіді
    top_results = results[:2]
    
    if language == "uk":
        response = f"За запитом '{query}' я знайшов:\n\n"
        for i, result in enumerate(top_results, 1):
            response += f"{i}. {result['title']}\n{result['snippet'][:150]}...\n\n"
        return response.strip()
    
    elif language == "de":
        response = f"Für '{query}' habe ich gefunden:\n\n"
        for i, result in enumerate(top_results, 1):
            response += f"{i}. {result['title']}\n{result['snippet'][:150]}...\n\n"
        return response.strip()
    
    else:  # en
        response = f"For '{query}' I found:\n\n"
        for i, result in enumerate(top_results, 1):
            response += f"{i}. {result['title']}\n{result['snippet'][:150]}...\n\n"
        return response.strip()


def extract_relevant_info(query: str, results: List[Dict[str, Any]]) -> str:
    """Витягує релевантну інформацію з результатів (legacy функція)"""
    if not results:
        return "Не знайдено релевантної інформації."
    
    # Беремо перший результат як найрелевантніший
    first = results[0]
    return f"{first.get('title', '')}: {first.get('snippet', '')}"
