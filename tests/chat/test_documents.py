import json
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from archivelens.chat.collection import Collection
from archivelens.chat.documents import DocumentCollection
from archivelens.chat.graph import build_graph
from archivelens.models import ArticleContent, Item


def test_document_search_returns_page_matches_without_full_page_text(tmp_path):
    text_file = tmp_path / 'document.txt'
    text_file.write_text('First page about hospitals and medical workers.\fSecond page about funding and governance.')

    document = DocumentCollection(text_file, title='Test document', read_radius=0)
    hits = document.search('hospitals medical', limit=1)

    assert hits[0]['title'] == 'Test document'
    assert hits[0]['page'] == 1
    assert hits[0]['read_start_page'] == 1
    assert hits[0]['read_end_page'] == 1
    assert 'excerpt' in hits[0]
    assert 'text' not in hits[0]


def test_document_read_returns_full_page_range(tmp_path):
    text_file = tmp_path / 'document.txt'
    text_file.write_text('First page.\fSecond page.\fThird page.')

    document = DocumentCollection(text_file, read_radius=0)

    result = document.read_pages(2, 3)
    assert result['start_page'] == 2
    assert result['end_page'] == 3
    assert '[Page 2]\nSecond page.' in result['text']
    assert '[Page 3]\nThird page.' in result['text']
    assert document.read_pages(0) == {'error': 'Invalid page range'}


def test_graph_exposes_bearing_witness_document_tools(tmp_path):
    item = Item(id=uuid4(), contents=[ArticleContent(
        id=uuid4(), url='https://example.org/news', title='News', text_body='News body',
    )])
    (tmp_path / 'item.json').write_text(item.model_dump_json())
    store = Collection(tmp_path)

    class FakeDocument:
        def search(self, query, limit=5):
            return [{'page': 4, 'read_start_page': 4, 'read_end_page': 5, 'excerpt': 'hospital evidence'}]

        def read_pages(self, start_page, end_page=None):
            return {'start_page': start_page, 'end_page': end_page, 'text': 'Full document evidence'}

    class DocumentModel:
        def bind_tools(self, tools):
            assert {t.name for t in tools} == {
                'search_items', 'read_item', 'search_bearing_witness_document', 'read_bearing_witness_pages'
            }
            return self

        def invoke(self, messages):
            results = [m for m in messages if isinstance(m, ToolMessage)]
            if not results:
                return AIMessage(content='', tool_calls=[dict(
                    name='search_bearing_witness_document', args={'query': 'hospital'}, id='search-doc'
                )])
            if len(results) == 1:
                hit = json.loads(results[0].content)[0]
                assert 'text' not in hit
                return AIMessage(content='', tool_calls=[dict(
                    name='read_bearing_witness_pages',
                    args={'start_page': hit['read_start_page'], 'end_page': hit['read_end_page']},
                    id='read-doc',
                )])
            return AIMessage(content=json.loads(results[-1].content)['text'])

    result = build_graph(
        store,
        DocumentModel(),
        prompt='Test system prompt.',
        document_collection=FakeDocument(),
        include_document=True,
    ).invoke({'messages': [HumanMessage(content='What does the document say about hospitals?')]})

    assert result['messages'][-1].content == 'Full document evidence'


def test_document_search_uses_embeddings_for_semantic_matches_without_keyword_overlap(tmp_path):
    text_file = tmp_path / 'document.txt'
    text_file.write_text('ambulances transported patients.\frecipes and kitchens.')

    class FakeEmbeddings:
        def embed_documents(self, texts):
            return [[1.0, 0.0] if 'ambulances' in text else [0.0, 1.0] for text in texts]

        def embed_query(self, text):
            return [1.0, 0.0]

    document = DocumentCollection(text_file, embeddings=FakeEmbeddings())
    hits = document.search('medical evacuation', limit=2)

    assert hits[0]['page'] == 1
    assert hits[0]['semantic_score'] > 0.99
    assert hits[0]['bm25_score'] == 0
    assert hits[0]['score'] == hits[0]['semantic_score']
    assert {hit['page'] for hit in hits} == {1}
