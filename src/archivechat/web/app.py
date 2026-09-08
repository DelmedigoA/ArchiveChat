"""Starlette app for the local ArchiveChat web UI."""

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from archivechat.chat.results import extract_read_items, item_summary, message_text


STATIC_DIR = Path(__file__).with_name('static')


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
        try:
            result = graph.invoke({'messages': [*messages, HumanMessage(content=question)]}, {'recursion_limit': 25})
        except Exception as exc:
            return JSONResponse({'error': 'Chat failed', 'detail': str(exc)}, status_code=500)

        result_messages = result['messages']
        messages[:] = result_messages
        read_items = [item_summary(item) for item in extract_read_items(result_messages)]
        return JSONResponse({
            'answer': message_text(result_messages[-1].content),
            'items': read_items,
        })

    routes = [
        Route('/', index),
        Route('/api/chat', chat, methods=['POST']),
    ]
    if static_dir is not None:
        routes.append(Mount('/static', StaticFiles(directory=static_dir), name='static'))
    return Starlette(routes=routes)
