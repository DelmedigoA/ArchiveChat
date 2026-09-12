"""Agent → tools → agent loop, with full-item reading."""

from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .collection import Collection
from .documents import DocumentCollection
from .faqs import FaqCollection
from .project_metadata import ProjectMetadataCollection
from .prompts import load_chat_prompt
from .tools.archive import make_archive_tools
from .tools.document import make_document_tools
from .tools.faq import make_faq_tools
from .tools.metadata import make_project_metadata_tools


def build_graph(
    collection: Collection,
    model,
    prompt: str | None = None,
    search_limit: int = 10,
    extra_tools: list[BaseTool] | None = None,
    faq_collection: FaqCollection | None = None,
    faq_search_limit: int = 5,
    document_collection: DocumentCollection | None = None,
    include_document: bool = False,
    document_search_limit: int = 5,
    project_metadata_collection: ProjectMetadataCollection | None = None,
):
    prompt = prompt or load_chat_prompt(include_document=include_document)
    tools = make_archive_tools(collection, search_limit)
    if project_metadata_collection:
        tools.extend(make_project_metadata_tools(project_metadata_collection))
    if include_document and document_collection:
        tools.extend(make_document_tools(document_collection, document_search_limit))
    if faq_collection:
        tools.extend(make_faq_tools(faq_collection, faq_search_limit))
    tools.extend(extra_tools or [])
    bound = model.bind_tools(tools)
    runtime_context = _runtime_context(
        collection, faq_collection, document_collection if include_document else None, project_metadata_collection,
        include_document=include_document,
    )
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
    include_document: bool = False,
) -> str:
    catalog_records = sum(1 for item in collection.items.values() if item.catalog_record is not None)
    item_count = len(collection.items)
    faq_count = len(getattr(faq_collection, 'faqs', {})) if faq_collection else 0
    document_pages = len(getattr(document_collection, 'pages', [])) if document_collection else 0
    metadata_count = len(getattr(project_metadata_collection, 'records', {})) if project_metadata_collection else 0
    context = (
        'Runtime collection status:\n'
        f'- Available inspectable archive catalog records/items: {catalog_records} catalog records across {item_count} items.\n'
        f'- Project FAQ metadata records available through dedicated FAQ tools: {faq_count}.\n'
        f'- Project metadata records available through dedicated metadata tools: {metadata_count}.\n'
        '- Project metadata is the first place to look for questions about ArchiveLens, Bearing Witness, the website, website navigation, sitemap/crawl inventory, the author Lee Mordechai, the About text, document identity, document structure, and version history.\n'
        '- When a user asks about a topic that maps to a Bearing Witness website project, report, map, article hub, testimony section, archive search page, FAQ page, or other public section, use project metadata to identify the most relevant section and recommend it at the end of the answer as navigation guidance. Use a Markdown link with the section title when metadata provides a URL. Omit this only when metadata does not identify a relevant section.\n'
        '- FAQ metadata is for specific FAQ-style questions such as funding, submissions, languages, methodology, scope, reliability, media use, and site usage.\n'
        '- Project metadata and FAQ metadata are context, not evidence for claims about events in Gaza.\n'
    )
    if include_document:
        document_title = getattr(document_collection, 'title', 'Bearing Witness document') if document_collection else 'not loaded'
        context += (
            f'- Main Bearing Witness document: {document_title}; searchable page count: {document_pages}.\n'
            "- Treat the Bearing Witness document as the project's main analytical source.\n"
            '- This is a beta ArchiveLens build: most references cited inside the Bearing Witness document do not yet have inspectable archive items/catalog records available in this chat.\n'
            '- When a document citation has no inspectable item, say that the document supports the point but the referenced source is not available for item-modal inspection here.'
        )
    return context
