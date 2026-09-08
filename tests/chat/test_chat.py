import json
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from archivechat.models import Item, ArticleContent
from archivechat.chat.collection import Collection
from archivechat.chat.graph import build_graph


def collection(tmp_path):
    item = Item(id=uuid4(), contents=[ArticleContent(
        id=uuid4(), url='https://example.org/news', title='Hospital transport',
        text_body='Ambulances carried patients.\n\n' + 'Full article paragraph. ' * 100,
    )])
    (tmp_path / 'item.json').write_text(item.model_dump_json())
    return Collection(tmp_path), item


def write_item(tmp_path, filename, title, text):
    item = Item(id=uuid4(), contents=[ArticleContent(
        id=uuid4(), url=f'https://example.org/{filename}', title=title, text_body=text,
    )])
    (tmp_path / filename).write_text(item.model_dump_json())
    return item


def test_search_and_full_read(tmp_path):
    store, item = collection(tmp_path)
    hits = store.search('ambulances')
    assert hits[0]['item_id'] == str(item.id)
    assert len(hits[0]['excerpt']) < len(item.contents[0].text_body)
    assert store.read(str(item.id))['contents'][0]['text_body'] == item.contents[0].text_body
    assert store.search('astronomy') == []
    assert store.search('  ') == []
    assert store.read('../secret') == {'error': 'Unknown item ID'}


def test_search_ranks_with_bm25_term_frequency(tmp_path):
    repeated = write_item(tmp_path, 'repeated.json', 'Repeated', 'israel israel israel aid')
    single = write_item(tmp_path, 'single.json', 'Single', 'israel aid')

    hits = Collection(tmp_path).search('israel')

    assert hits[0]['item_id'] == str(repeated.id)
    assert hits[0]['score'] > hits[1]['score']
    assert {hit['item_id'] for hit in hits} == {str(repeated.id), str(single.id)}


def test_search_penalizes_longer_items_with_same_term_frequency(tmp_path):
    short = write_item(tmp_path, 'short.json', 'Short', 'israel aid')
    long = write_item(tmp_path, 'long.json', 'Long', 'israel ' + 'background ' * 100)

    hits = Collection(tmp_path).search('israel')

    assert hits[0]['item_id'] == str(short.id)
    assert hits[0]['score'] > hits[1]['score']


def test_search_uses_embeddings_for_semantic_matches_without_keyword_overlap(tmp_path):
    hospitals = write_item(tmp_path, 'hospitals.json', 'Hospitals', 'ambulances transported patients')
    cooking = write_item(tmp_path, 'cooking.json', 'Cooking', 'recipes and kitchens')

    class FakeEmbeddings:
        def embed_documents(self, texts):
            return [[1.0, 0.0] if 'ambulances' in text else [0.0, 1.0] for text in texts]

        def embed_query(self, text):
            return [1.0, 0.0]

    hits = Collection(tmp_path, embeddings=FakeEmbeddings()).search('medical evacuation')

    assert hits[0]['item_id'] == str(hospitals.id)
    assert hits[0]['semantic_score'] > 0.99
    assert hits[0]['bm25_score'] == 0
    assert hits[0]['score'] == hits[0]['semantic_score']
    assert str(cooking.id) not in {hit['item_id'] for hit in hits}


def test_graph_searches_reads_and_answers(tmp_path):
    store, item = collection(tmp_path)
    prompt = 'Test system prompt.'

    class ScriptedModel:
        def bind_tools(self, tools):
            assert {t.name for t in tools} == {'search_items', 'read_item'}
            return self

        def invoke(self, messages):
            assert messages[0].content.startswith(prompt)
            assert 'Runtime collection status:' in messages[0].content
            assert 'Available inspectable archive catalog records/items: 0 catalog records across 1 items.' in messages[0].content
            assert 'Main Bearing Witness document: not loaded; searchable page count: 0.' in messages[0].content
            assert 'beta ArchiveLens build' in messages[0].content
            results = [m for m in messages if isinstance(m, ToolMessage)]
            if not results:
                return AIMessage(content='', tool_calls=[dict(name='search_items', args={'query': 'ambulances'}, id='search')])
            if len(results) == 1:
                hit = json.loads(results[0].content)[0]
                return AIMessage(content='', tool_calls=[dict(name='read_item', args={'item_id': hit['item_id']}, id='read')])
            body = json.loads(results[-1].content)['contents'][0]['text_body']
            assert body == item.contents[0].text_body
            return AIMessage(content='Ambulances carried patients. [Source](https://example.org/news)')

    result = build_graph(store, ScriptedModel(), prompt=prompt).invoke({'messages': [HumanMessage(content='How were patients transported?')]})
    assert 'Ambulances carried patients' in result['messages'][-1].content
    assert len([m for m in result['messages'] if isinstance(m, ToolMessage)]) == 2


def test_graph_accepts_extra_tools(tmp_path):
    store, _ = collection(tmp_path)

    class ExtraToolModel:
        def bind_tools(self, tools):
            assert {t.name for t in tools} == {'search_items', 'read_item', 'search_wikipedia'}
            return self

        def invoke(self, messages):
            return AIMessage(content='Ready.')

    def search_wikipedia(query: str) -> list[dict]:
        """Search Wikipedia."""
        return [{'title': query}]

    search_wikipedia.name = 'search_wikipedia'

    result = build_graph(
        store,
        ExtraToolModel(),
        prompt='Test system prompt.',
        extra_tools=[search_wikipedia],
    ).invoke({'messages': [HumanMessage(content='hi')]})

    assert result['messages'][-1].content == 'Ready.'


def test_tool_loop_is_bounded(tmp_path):
    import pytest
    from langgraph.errors import GraphRecursionError

    store, _ = collection(tmp_path)

    class LoopingModel:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return AIMessage(content='', tool_calls=[dict(name='search_items', args={'query': 'ambulances'}, id=str(uuid4()))])

    with pytest.raises(GraphRecursionError):
        build_graph(store, LoopingModel()).invoke(
            {'messages': [HumanMessage(content='Search forever')]},
            {'recursion_limit': 5},
        )


def test_graph_uses_configured_default_search_limit(tmp_path):
    store, _ = collection(tmp_path)
    seen_limits = []

    def search(query, limit=10):
        seen_limits.append(limit)
        return []

    store.search = search

    class SearchOnlyModel:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            results = [m for m in messages if isinstance(m, ToolMessage)]
            if not results:
                return AIMessage(content='', tool_calls=[dict(name='search_items', args={'query': 'ambulances'}, id='search')])
            return AIMessage(content='No matches.')

    build_graph(store, SearchOnlyModel(), prompt='Test system prompt.', search_limit=7).invoke(
        {'messages': [HumanMessage(content='Search ambulances')]}
    )

    assert seen_limits == [7]



def test_graph_exposes_project_metadata_tools_when_configured(tmp_path):
    store, _ = collection(tmp_path)

    class FakeMetadata:
        records = {'project-overview': {'title': 'Project overview'}}

        def list_records(self):
            return [{
                'record_id': 'project-overview',
                'kind': 'project_metadata',
                'title': 'Project overview',
                'description': 'Project context',
                'language': 'en',
            }]

        def read(self, record_id):
            return {
                'record_id': record_id,
                'kind': 'project_metadata',
                'title': 'Project overview',
                'content': 'Full metadata context.',
            }

    class MetadataModel:
        def bind_tools(self, tools):
            assert {t.name for t in tools} == {
                'search_items', 'read_item', 'list_project_metadata_records', 'read_project_metadata_record'
            }
            return self

        def invoke(self, messages):
            assert 'metadata tools: 1' in messages[0].content
            assert 'not evidence for claims about events in Gaza' in messages[0].content
            results = [m for m in messages if isinstance(m, ToolMessage)]
            if not results:
                return AIMessage(content='', tool_calls=[dict(
                    name='list_project_metadata_records', args={}, id='list-metadata'
                )])
            if len(results) == 1:
                listed = json.loads(results[0].content)[0]
                assert 'content' not in listed
                return AIMessage(content='', tool_calls=[dict(
                    name='read_project_metadata_record',
                    args={'record_id': listed['record_id']},
                    id='read-metadata',
                )])
            return AIMessage(content=json.loads(results[-1].content)['content'])

    result = build_graph(
        store,
        MetadataModel(),
        prompt='Test system prompt.',
        project_metadata_collection=FakeMetadata(),
    ).invoke({'messages': [HumanMessage(content='What is this project?')]})

    assert result['messages'][-1].content == 'Full metadata context.'


def test_graph_exposes_faq_tools_when_configured(tmp_path):
    store, _ = collection(tmp_path)

    class FakeFaqs:
        def search(self, query, limit=5):
            return [{'faq_id': 'faq-1', 'question': 'Who manages the project?', 'score': 1.0}]

        def read(self, faq_id):
            return {'faq_id': faq_id, 'question': 'Who manages the project?', 'answer': 'A full FAQ answer.'}

    class FaqModel:
        def bind_tools(self, tools):
            assert {t.name for t in tools} == {'search_items', 'read_item', 'search_faqs', 'read_faq'}
            return self

        def invoke(self, messages):
            results = [m for m in messages if isinstance(m, ToolMessage)]
            if not results:
                return AIMessage(content='', tool_calls=[dict(name='search_faqs', args={'query': 'who manages'}, id='search-faq')])
            if len(results) == 1:
                hit = json.loads(results[0].content)[0]
                assert 'answer' not in hit
                return AIMessage(content='', tool_calls=[dict(name='read_faq', args={'faq_id': hit['faq_id']}, id='read-faq')])
            answer = json.loads(results[-1].content)['answer']
            return AIMessage(content=answer)

    result = build_graph(
        store,
        FaqModel(),
        prompt='Test system prompt.',
        faq_collection=FakeFaqs(),
    ).invoke({'messages': [HumanMessage(content='Who manages this project?')]})

    assert result['messages'][-1].content == 'A full FAQ answer.'


def test_runtime_context_counts_catalog_faq_document_and_metadata_records(tmp_path):
    item = write_item(tmp_path, 'with_catalog.json', 'With catalog', 'archive body')
    # Reuse the fixture-like item_data shape indirectly by attaching a catalog-free item above,
    # then verify the runtime context still reports item count separately from catalog count.

    class FakeFaqs:
        faqs = {'faq-1': {}, 'faq-2': {}}

    class FakeDocument:
        title = 'Bearing Witness Test Document'
        pages = [object(), object(), object()]

    class FakeMetadata:
        records = {'project-overview': {}, 'document-record': {}}

    class PromptCaptureModel:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            return AIMessage(content=messages[0].content)

    result = build_graph(
        Collection(tmp_path),
        PromptCaptureModel(),
        prompt='Base prompt.',
        faq_collection=FakeFaqs(),
        document_collection=FakeDocument(),
        project_metadata_collection=FakeMetadata(),
    ).invoke({'messages': [HumanMessage(content='status?')]})

    content = result['messages'][-1].content
    assert 'Available inspectable archive catalog records/items: 0 catalog records across 1 items.' in content
    assert 'Project FAQ metadata records available through dedicated FAQ tools: 2.' in content
    assert 'Project metadata records available through dedicated metadata tools: 2.' in content
    assert 'Project metadata and FAQ metadata describe ArchiveLens, Bearing Witness, the document structure' in content
    assert 'not evidence for claims about events in Gaza' in content
    assert 'Main Bearing Witness document: Bearing Witness Test Document; searchable page count: 3.' in content
    assert "Treat the Bearing Witness document as the project's main analytical source." in content
    assert 'most references cited inside the Bearing Witness document do not yet have inspectable archive items' in content
