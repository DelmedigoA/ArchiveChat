import json
from types import SimpleNamespace
from uuid import uuid4

from langchain_core.messages import AIMessage, ToolMessage
from starlette.testclient import TestClient

from archivechat.models import ArticleContent, Item
from archivechat.web.app import create_app


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
