"""Agent → tools → agent loop, with full-item reading."""

from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .collection import Collection
from .documents import DocumentCollection
from .faqs import FaqCollection
from .project_metadata import ProjectMetadataCollection
from .prompts import load_chat_prompt


def build_graph(
    collection: Collection,
    model,
    prompt: str | None = None,
    search_limit: int = 10,
    extra_tools: list[BaseTool] | None = None,
    faq_collection: FaqCollection | None = None,
    faq_search_limit: int = 5,
    document_collection: DocumentCollection | None = None,
    document_search_limit: int = 5,
    project_metadata_collection: ProjectMetadataCollection | None = None,
):
    prompt = prompt or load_chat_prompt()
    if search_limit < 1:
        raise ValueError('search_limit must be at least 1')
    if faq_search_limit < 1:
        raise ValueError('faq_search_limit must be at least 1')
    if document_search_limit < 1:
        raise ValueError('document_search_limit must be at least 1')

    @tool
    def search_items(query: str, limit: int = search_limit) -> list[dict]:
        """Find candidate items by keywords in catalog metadata and article text."""
        return collection.search(query, limit)

    @tool
    def read_item(item_id: str) -> dict:
        """Read an entire item, including its catalog, full articles, and representations."""
        return collection.read(item_id)

    tools = [search_items, read_item]
    if project_metadata_collection:
        @tool
        def list_project_metadata_records() -> list[dict]:
            """List project-level metadata records. These describe the project/document; they are not event evidence."""
            return project_metadata_collection.list_records()

        @tool
        def read_project_metadata_record(record_id: str) -> dict:
            """Read a project-level metadata record. Use for ArchiveLens/Bearing Witness context, not event evidence."""
            return project_metadata_collection.read(record_id)

        tools.extend([list_project_metadata_records, read_project_metadata_record])
    if document_collection:
        @tool
        def search_bearing_witness_document(query: str, limit: int = document_search_limit) -> list[dict]:
            """Find matching pages in the Bearing Witness Gaza document. Returns page matches, not full text."""
            return document_collection.search(query, limit)

        @tool
        def read_bearing_witness_pages(start_page: int, end_page: int | None = None) -> dict:
            """Read full text from selected Bearing Witness document pages."""
            return document_collection.read_pages(start_page, end_page)

        tools.extend([search_bearing_witness_document, read_bearing_witness_pages])
    if faq_collection:
        @tool
        def search_faqs(query: str, limit: int = faq_search_limit) -> list[dict]:
            """Find FAQ questions relevant to project context, methodology, scope, or usage."""
            return faq_collection.search(query, limit)

        @tool
        def read_faq(faq_id: str) -> dict:
            """Read the full FAQ answer for a question returned by search_faqs."""
            return faq_collection.read(faq_id)

        tools.extend([search_faqs, read_faq])
    tools.extend(extra_tools or [])
    bound = model.bind_tools(tools)
    runtime_context = _runtime_context(collection, faq_collection, document_collection, project_metadata_collection)
    full_prompt = f'{prompt}\n\n{runtime_context}'

    def agent(state: MessagesState):
        return {'messages': [bound.invoke([SystemMessage(content=full_prompt), *state['messages']])]}

    graph = StateGraph(MessagesState)
    graph.add_node('agent', agent)
    graph.add_node('tools', ToolNode(tools))
    graph.add_edge(START, 'agent')
    graph.add_conditional_edges('agent', tools_condition)
    graph.add_edge('tools', 'agent')
    return graph.compile()


def _runtime_context(
    collection: Collection,
    faq_collection: FaqCollection | None,
    document_collection: DocumentCollection | None,
    project_metadata_collection: ProjectMetadataCollection | None,
) -> str:
    catalog_records = sum(1 for item in collection.items.values() if item.catalog_record is not None)
    item_count = len(collection.items)
    faq_count = len(getattr(faq_collection, 'faqs', {})) if faq_collection else 0
    document_pages = len(getattr(document_collection, 'pages', [])) if document_collection else 0
    metadata_count = len(getattr(project_metadata_collection, 'records', {})) if project_metadata_collection else 0
    document_title = getattr(document_collection, 'title', 'Bearing Witness document') if document_collection else 'not loaded'
    return (
        'Runtime collection status:\n'
        f'- Available inspectable archive catalog records/items: {catalog_records} catalog records across {item_count} items.\n'
        f'- Project FAQ records available through dedicated FAQ tools: {faq_count}.\n'
        f'- Project metadata records available through dedicated metadata tools: {metadata_count}.\n'
        '- Project metadata describes ArchiveLens, Bearing Witness, the document structure, version history, and author/about-document context; it is context, not evidence for claims about events in Gaza.\n'
        f'- Main Bearing Witness document: {document_title}; searchable page count: {document_pages}.\n'
        "- Treat the Bearing Witness document as the project's main analytical source.\n"
        '- This is a beta ArchiveLens build: most references cited inside the Bearing Witness document do not yet have inspectable archive items/catalog records available in this chat.\n'
        '- When a document citation has no inspectable item, say that the document supports the point but the referenced source is not available for item-modal inspection here.'
    )
