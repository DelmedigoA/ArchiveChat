"""Optional web lookup tools for the chat agent."""

import html
import re
from typing import Protocol
from urllib.parse import quote, urlparse

import httpx
from langchain_core.tools import tool

HEADERS = {'User-Agent': 'ArchiveLens/0.1 (research assistant; contact: local)'}


class HttpClient(Protocol):
    def get(self, url: str, params: dict | None = None, headers: dict | None = None, timeout: int | None = None): ...


def make_web_tools(client: HttpClient | None = None):
    client = client or httpx.Client(follow_redirects=True)

    @tool
    def search_wikipedia(query: str, limit: int = 5) -> list[dict] | dict:
        """Search English Wikipedia for background pages related to a query."""
        try:
            response = client.get(
                'https://en.wikipedia.org/w/api.php',
                params={
                    'action': 'query',
                    'format': 'json',
                    'list': 'search',
                    'srsearch': query,
                    'srlimit': max(1, min(limit, 10)),
                },
                headers=HEADERS,
                timeout=20,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return {'error': 'Wikipedia search failed', 'detail': str(exc)}
        results = response.json().get('query', {}).get('search', [])
        return [
            {
                'title': result['title'],
                'snippet': _clean_text(result.get('snippet', '')),
                'url': f"https://en.wikipedia.org/wiki/{quote(result['title'].replace(' ', '_'))}",
            }
            for result in results
        ]

    @tool
    def read_wikipedia_summary(title: str) -> dict:
        """Read the lead summary for an English Wikipedia page title."""
        try:
            response = client.get(
                'https://en.wikipedia.org/w/api.php',
                params={
                    'action': 'query',
                    'format': 'json',
                    'prop': 'extracts',
                    'exintro': True,
                    'explaintext': True,
                    'redirects': True,
                    'titles': title,
                },
                headers=HEADERS,
                timeout=20,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return {'error': 'Wikipedia summary failed', 'detail': str(exc)}
        pages = response.json().get('query', {}).get('pages', {})
        page = next(iter(pages.values()), {})
        page_title = page.get('title', title)
        return {
            'title': page_title,
            'summary': page.get('extract', ''),
            'url': f"https://en.wikipedia.org/wiki/{quote(page_title.replace(' ', '_'))}",
        }

    @tool
    def fetch_web_page_text(url: str) -> dict:
        """Fetch readable text from a public HTTP or HTTPS page by URL."""
        parsed = urlparse(url)
        if parsed.scheme not in {'http', 'https'}:
            return {'error': 'Only http and https URLs are supported'}
        try:
            response = client.get(
                url,
                headers=HEADERS,
                timeout=20,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            return {'error': 'Web page fetch failed', 'detail': str(exc), 'url': url}
        return {'url': url, 'text': _clean_text(response.text)[:5000]}

    return [search_wikipedia, read_wikipedia_summary, fetch_web_page_text]


def _clean_text(text: str) -> str:
    text = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()
