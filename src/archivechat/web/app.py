"""Starlette app for the local ArchiveLens web UI."""

import json
from pathlib import Path
from typing import Any, AsyncIterator

from langchain_core.messages import HumanMessage
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from archivechat.chat.results import _json_from_content, extract_read_items, item_summary, message_text


STATIC_DIR = Path(__file__).with_name('static')


TOOL_STATUS = {
    'search_items': 'Searching the archive…',
    'read_item': 'Reading archive records…',
    'search_bearing_witness_document': 'Searching the Bearing Witness document…',
    'read_bearing_witness_pages': 'Reading document pages…',
    'list_project_metadata_records': 'Checking project context…',
    'read_project_metadata_record': 'Checking project context…',
    'search_faqs': 'Checking FAQ metadata…',
    'read_faq': 'Checking FAQ metadata…',
    'search_wikipedia': 'Checking public web context…',
    'read_wikipedia_summary': 'Checking public web context…',
    'fetch_web_page_text': 'Checking public web context…',
}


def sse(event: str, payload: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def chunk_text(chunk: Any) -> str:
    content = getattr(chunk, 'content', None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_blocks = [
            block['text']
            for block in content
            if isinstance(block, dict)
            and block.get('type') in {'text', 'output_text'}
            and isinstance(block.get('text'), str)
        ]
        return ''.join(text_blocks)
    return ''


def final_payload(result_messages: list[Any], start_index: int = 0) -> dict[str, Any]:
    current_turn_messages = result_messages[start_index:]
    return {
        'answer': message_text(result_messages[-1].content),
        'items': [item_summary(item) for item in extract_read_items(current_turn_messages)],
    }


def item_from_tool_event(event: dict[str, Any]) -> dict[str, Any] | None:
    if event.get('event') != 'on_tool_end' or event.get('name') != 'read_item':
        return None
    output = event.get('data', {}).get('output')
    payload = None
    if isinstance(output, dict):
        payload = output
    else:
        payload = _json_from_content(getattr(output, 'content', None))
    if isinstance(payload, dict) and payload.get('id') and payload.get('contents') is not None:
        return item_summary(payload)
    return None


def result_messages_from_event(event: dict[str, Any]) -> list[Any] | None:
    output = event.get('data', {}).get('output')
    if isinstance(output, dict) and isinstance(output.get('messages'), list) and output['messages']:
        return output['messages']
    return None


def create_app(graph: Any, initial_messages: list[Any] | None = None, static_dir: Path | None = STATIC_DIR) -> Starlette:
    messages = list(initial_messages or [])

    async def index(request: Request):
        if static_dir is None:
            return JSONResponse({'ok': True})
        return FileResponse(static_dir / 'index.html')

    async def chat(request: Request):
        payload = await request.json()
        question = str(payload.get('question') or '').strip()
        if not question:
            return JSONResponse({'error': 'Question is required'}, status_code=400)
        turn_start_index = len(messages)
        try:
            result = graph.invoke({'messages': [*messages, HumanMessage(content=question)]}, {'recursion_limit': 25})
        except Exception as exc:
            return JSONResponse({'error': 'Chat failed', 'detail': str(exc)}, status_code=500)

        result_messages = result['messages']
        messages[:] = result_messages
        return JSONResponse(final_payload(result_messages, turn_start_index))

    async def chat_stream(request: Request):
        payload = await request.json()
        question = str(payload.get('question') or '').strip()
        if not question:
            return JSONResponse({'error': 'Question is required'}, status_code=400)

        async def events() -> AsyncIterator[str]:
            turn_start_index = len(messages)
            final_messages = None
            emitted_text = False
            emitted_item_ids = set()
            last_status = None
            try:
                last_status = 'Working…'
                yield sse('status', {'message': last_status})
                async for event in graph.astream_events(
                    {'messages': [*messages, HumanMessage(content=question)]},
                    {'recursion_limit': 25},
                    version='v2',
                ):
                    event_type = event.get('event')
                    name = event.get('name')
                    if event_type == 'on_tool_start' and name in TOOL_STATUS:
                        status = TOOL_STATUS[name]
                        if status != last_status:
                            last_status = status
                            yield sse('status', {'message': status, 'tool': name})
                    elif event_type == 'on_chat_model_stream':
                        text = chunk_text(event.get('data', {}).get('chunk'))
                        if text:
                            emitted_text = True
                            if last_status != 'Writing answer…':
                                last_status = 'Writing answer…'
                                yield sse('status', {'message': last_status})
                            yield sse('delta', {'text': text})
                    item = item_from_tool_event(event)
                    if item and item.get('item_id') not in emitted_item_ids:
                        emitted_item_ids.add(item.get('item_id'))
                        yield sse('item', {'item': item})
                    maybe_messages = result_messages_from_event(event)
                    if maybe_messages:
                        final_messages = maybe_messages

                if final_messages is None:
                    raise RuntimeError('Streaming completed without final graph messages')
                messages[:] = final_messages
                yield sse('final', {**final_payload(final_messages, turn_start_index), 'replace': emitted_text})
                yield sse('done', {})
            except Exception as exc:
                yield sse('error', {'message': 'Chat failed', 'detail': str(exc)})

        return StreamingResponse(events(), media_type='text/event-stream')

    routes = [
        Route('/', index),
        Route('/api/chat', chat, methods=['POST']),
        Route('/api/chat/stream', chat_stream, methods=['POST']),
    ]
    if static_dir is not None:
        routes.append(Mount('/static', StaticFiles(directory=static_dir), name='static'))
    return Starlette(routes=routes)
