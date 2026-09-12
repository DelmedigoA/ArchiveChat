import json
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage
from starlette.testclient import TestClient

from archivelens.models import ArticleContent, Item
from archivelens.web.app import chunk_text, create_app, item_from_tool_event


def test_chat_api_returns_answer_and_read_items():
    item = Item(
        id=uuid4(),
        contents=[
            ArticleContent(
                id=uuid4(),
                url='https://example.org/source',
                title='Source title',
                text_body='Source body',
            )
        ],
    )

    class FakeGraph:
        def invoke(self, payload, config):
            return {
                'messages': [
                    *payload['messages'],
                    ToolMessage(content=json.dumps(item.model_dump(mode='json')), tool_call_id='read-1', name='read_item'),
                    AIMessage(content='Answer with [Source title](https://example.org/source).'),
                ]
            }

    app = create_app(
        graph=FakeGraph(),
        initial_messages=[],
        static_dir=None,
    )

    response = TestClient(app).post('/api/chat', json={'question': 'What happened?'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['answer'] == 'Answer with [Source title](https://example.org/source).'
    assert payload['items'][0]['item_id'] == str(item.id)
    assert payload['items'][0]['url'] == 'https://example.org/source'


def test_chat_api_rejects_empty_question():
    app = create_app(graph=SimpleNamespace(), initial_messages=[], static_dir=None)

    response = TestClient(app).post('/api/chat', json={'question': '  '})

    assert response.status_code == 400


def test_chat_reset_clears_conversation_history():
    app = create_app(graph=SimpleNamespace(), initial_messages=['old message'], static_dir=None)

    response = TestClient(app).post('/api/chat/reset')

    assert response.status_code == 200
    assert response.json() == {'ok': True}



def test_document_config_returns_deployment_managed_pdf_url():
    app = create_app(
        graph=SimpleNamespace(),
        initial_messages=[],
        static_dir=None,
        document_pdf_url='https://assets.example.org/documents/bearing-witness-gaza-english-v6.7.0.pdf',
    )

    response = TestClient(app).get('/api/document-config')

    assert response.status_code == 200
    assert response.json() == {
        'pdf_url': 'https://assets.example.org/documents/bearing-witness-gaza-english-v6.7.0.pdf',
        'title': 'Bearing Witness – Gaza',
        'version': 'English v6.7.0 · July 5, 2025',
    }


def test_document_config_reports_when_no_pdf_is_configured():
    app = create_app(graph=SimpleNamespace(), initial_messages=[], static_dir=None)

    assert TestClient(app).get('/api/document-config').json()['pdf_url'] == ''


def test_local_document_asset_is_served_with_byte_ranges(tmp_path):
    pdf_path = tmp_path / 'bearing-witness.pdf'
    pdf_path.write_bytes(b'%PDF-test-document')
    app = create_app(
        graph=SimpleNamespace(),
        initial_messages=[],
        static_dir=None,
        document_pdf_url='/documents/bearing-witness-gaza-english-v6.7.0.pdf',
        document_pdf_path=pdf_path,
    )

    response = TestClient(app).get('/documents/bearing-witness-gaza-english-v6.7.0.pdf', headers={'Range': 'bytes=0-4'})

    assert response.status_code == 206
    assert response.content == b'%PDF-'
    assert response.headers['accept-ranges'] == 'bytes'



def test_chat_stream_returns_status_deltas_final_items_and_done():
    item = Item(
        id=uuid4(),
        contents=[
            ArticleContent(
                id=uuid4(),
                url='https://example.org/source',
                title='Source title',
                text_body='Source body',
            )
        ],
    )

    class FakeChunk:
        content = 'Streaming answer'

    class FakeGraph:
        async def astream_events(self, payload, config, version='v2'):
            assert version == 'v2'
            yield {'event': 'on_tool_start', 'name': 'search_items', 'data': {}}
            yield {'event': 'on_tool_start', 'name': 'read_item', 'data': {}}
            yield {'event': 'on_tool_end', 'name': 'read_item', 'data': {'output': ToolMessage(content=json.dumps(item.model_dump(mode='json')), tool_call_id='read-1', name='read_item')}}
            yield {'event': 'on_chat_model_stream', 'name': 'model', 'data': {'chunk': FakeChunk()}}
            yield {'event': 'on_chain_end', 'name': 'LangGraph', 'data': {'output': {'messages': [
                *payload['messages'],
                ToolMessage(content=json.dumps(item.model_dump(mode='json')), tool_call_id='read-1', name='read_item'),
                AIMessage(content='Final [Source title](https://example.org/source).'),
            ]}}}

    app = create_app(graph=FakeGraph(), initial_messages=[], static_dir=None)

    with TestClient(app).stream('POST', '/api/chat/stream', json={'question': 'What happened?'}) as response:
        body = response.read().decode()

    assert response.status_code == 200
    assert 'event: status' in body
    assert 'Searching the archive' in body
    assert 'Reading archive records' in body
    assert 'event: item' in body
    assert 'event: delta' in body
    assert 'Streaming answer' in body
    assert 'event: final' in body
    assert 'Final [Source title](https://example.org/source).' in body
    assert str(item.id) in body
    assert 'event: done' in body


def test_chat_stream_rejects_empty_question():
    app = create_app(graph=SimpleNamespace(), initial_messages=[], static_dir=None)

    response = TestClient(app).post('/api/chat/stream', json={'question': '  '})

    assert response.status_code == 400



def test_chunk_text_filters_responses_api_non_text_blocks():
    class Chunk:
        content = [
            {'type': 'reasoning', 'summary': []},
            {'type': 'function_call', 'name': 'search_items', 'arguments': '{}'},
            {'type': 'output_text', 'text': 'Visible answer'},
        ]

    assert chunk_text(Chunk()) == 'Visible answer'



def test_item_from_tool_event_extracts_read_item_summary():
    item = Item(
        id=uuid4(),
        contents=[ArticleContent(id=uuid4(), url='https://example.org/source', title='Source title', text_body='Source body')],
    )
    event = {
        'event': 'on_tool_end',
        'name': 'read_item',
        'data': {'output': ToolMessage(content=json.dumps(item.model_dump(mode='json')), tool_call_id='read-1', name='read_item')},
    }

    summary = item_from_tool_event(event)

    assert summary['item_id'] == str(item.id)
    assert summary['title'] == 'Source title'
    assert summary['url'] == 'https://example.org/source'


def test_item_from_tool_event_ignores_non_read_item_events():
    assert item_from_tool_event({'event': 'on_tool_end', 'name': 'search_items', 'data': {'output': []}}) is None
