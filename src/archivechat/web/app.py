"""Starlette app for the local ArchiveLens web UI."""

from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

# Re-export existing helpers so callers can keep their original imports.
from .streaming import (
    TOOL_STATUS,
    chunk_text,
    final_payload,
    item_from_tool_event,
    result_messages_from_event,
    sse,
    stream_chat_events,
)


STATIC_DIR = Path(__file__).with_name('static')
DOCUMENT_PDF_PATH = Path(__file__).resolve().parents[3] / 'Gaza_English-v6.7.0-5.7.25 (2).pdf'
DOCUMENT_PDF_ROUTE = '/documents/bearing-witness-gaza-english-v6.7.0.pdf'


def create_app(
    graph: Any,
    initial_messages: list[Any] | None = None,
    static_dir: Path | None = STATIC_DIR,
    document_pdf_url: str | None = None,
    document_pdf_path: Path | None = DOCUMENT_PDF_PATH,
) -> Starlette:
    messages = list(initial_messages or [])

    async def index(request: Request):
        if static_dir is None:
            return JSONResponse({'ok': True})
        return FileResponse(static_dir / 'index.html')

    async def document_config(request: Request):
        """Expose the public, deployment-managed PDF location to the lazy viewer."""
        return JSONResponse(
            {
                'pdf_url': document_pdf_url or '',
                'title': 'Bearing Witness – Gaza',
                'version': 'English v6.7.0 · July 5, 2025',
            }
        )

    async def document_pdf(request: Request):
        """Serve the local development asset with byte-range support when present."""
        if document_pdf_path is None or not document_pdf_path.is_file():
            return JSONResponse(
                {'detail': 'Bearing Witness PDF asset is unavailable'}, status_code=404
            )
        return FileResponse(document_pdf_path, media_type='application/pdf')

    async def chat(request: Request):
        payload = await request.json()
        question = str(payload.get('question') or '').strip()
        if not question:
            return JSONResponse({'error': 'Question is required'}, status_code=400)
        turn_start_index = len(messages)
        try:
            result = graph.invoke(
                {'messages': [*messages, HumanMessage(content=question)]}, {'recursion_limit': 25}
            )
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

        return StreamingResponse(
            stream_chat_events(graph, messages, question),
            media_type='text/event-stream',
        )

    routes = [
        Route('/', index),
        Route('/api/document-config', document_config),
        Route(DOCUMENT_PDF_ROUTE, document_pdf),
        Route('/api/chat', chat, methods=['POST']),
        Route('/api/chat/stream', chat_stream, methods=['POST']),
    ]
    if static_dir is not None:
        routes.append(Mount('/static', StaticFiles(directory=static_dir), name='static'))
    return Starlette(routes=routes)
