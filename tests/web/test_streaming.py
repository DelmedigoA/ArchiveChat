"""Exact stream ordering and history behavior at the HTTP boundary."""

import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage
from starlette.testclient import TestClient

from archivechat.web.app import create_app


def read_events(response):
    events = []
    for block in response.text.strip().split('\n\n'):
        event, data = block.split('\n')
        events.append((event.removeprefix('event: '), json.loads(data.removeprefix('data: '))))
    return events


@pytest.mark.parametrize('stream_text', [False, True])
def test_stream_deduplicates_statuses_and_replaces_only_when_text_was_sent(stream_text):
    class Graph:
        async def astream_events(self, payload, config, version):
            assert config == {'recursion_limit': 25}
            assert version == 'v2'
            for name in ['search_items', 'search_items', 'read_faq', 'search_faqs']:
                yield {'event': 'on_tool_start', 'name': name}
            if stream_text:
                yield {'event': 'on_chat_model_stream', 'data': {'chunk': SimpleNamespace(content='שלום')}}
            yield {'data': {'output': {'messages': [*payload['messages'], AIMessage(content='Final')]}}}

    response = TestClient(create_app(Graph(), static_dir=None)).post('/api/chat/stream', json={'question': 'hi'})

    expected = [
        ('status', {'message': 'Reviewing material…'}),
        ('status', {'message': 'Searching the archive…', 'tool': 'search_items'}),
        ('status', {'message': 'Checking FAQ metadata…', 'tool': 'read_faq'}),
    ]
    if stream_text:
        expected += [('status', {'message': 'Writing answer…'}), ('delta', {'text': 'שלום'})]
    expected += [('final', {'answer': 'Final', 'items': [], 'replace': stream_text}), ('done', {})]
    assert read_events(response) == expected


@pytest.mark.parametrize('failure', ['exception', 'missing-final'])
def test_failed_stream_keeps_previous_history_and_emits_no_done(failure):
    class Graph:
        def __init__(self):
            self.inputs = []

        async def astream_events(self, payload, config, version):
            self.inputs.append(payload['messages'])
            if failure == 'exception':
                raise ValueError('Original error')
            yield {'event': 'on_tool_start', 'name': 'unknown'}

    graph = Graph()
    initial = [AIMessage(content='Prior answer')]
    client = TestClient(create_app(graph, initial_messages=initial, static_dir=None))

    for question in ['first', 'second']:
        events = read_events(client.post('/api/chat/stream', json={'question': question}))
        detail = 'Original error' if failure == 'exception' else 'Streaming completed without final graph messages'
        assert events == [
            ('status', {'message': 'Reviewing material…'}),
            ('error', {'message': 'Chat failed', 'detail': detail}),
        ]
    assert [[message.content for message in messages] for messages in graph.inputs] == [
        ['Prior answer', 'first'], ['Prior answer', 'second'],
    ]
    assert len(initial) == 1
