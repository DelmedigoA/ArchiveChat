"""Helpers for turning graph results into UI payloads."""

import json
from typing import Any


def message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_blocks = [
            block['text']
            for block in content
            if isinstance(block, dict) and block.get('type') in {'text', 'output_text'} and isinstance(block.get('text'), str)
        ]
        if text_blocks:
            return '\n'.join(text_blocks)
    return str(content)


def extract_read_items(messages: list[Any]) -> list[dict]:
    items = []
    for message in messages:
        if getattr(message, 'name', None) != 'read_item':
            continue
        payload = _json_from_content(getattr(message, 'content', None))
        if isinstance(payload, dict) and payload.get('id') and payload.get('contents') is not None:
            items.append(payload)
    return items


def item_summary(item: dict) -> dict:
    catalog = item.get('catalog_record') or {}
    contents = item.get('contents') or []
    first_content = contents[0] if contents else {}
    url = catalog.get('link') or first_content.get('url') or ''
    title = catalog.get('english_title') or first_content.get('title') or 'Untitled item'
    return {
        'item_id': item.get('id'),
        'title': title,
        'hebrew_title': catalog.get('hebrew_title'),
        'description': catalog.get('english_description') or '',
        'hebrew_description': catalog.get('hebrew_description'),
        'url': url,
        'catalog': catalog,
        'contents': contents,
    }


def _json_from_content(content: Any):
    if isinstance(content, str):
        return _loads(content)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and isinstance(block.get('text'), str):
                parsed = _loads(block['text'])
                if parsed is not None:
                    return parsed
    return None


def _loads(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None
