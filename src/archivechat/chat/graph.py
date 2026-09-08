"""Agent → tools → agent loop, with full-item reading."""

from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .collection import Collection
from .documents import DocumentCollection
from .faqs import FaqCollection
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

    def agent(state: MessagesState):
        return {'messages': [bound.invoke([SystemMessage(content=prompt), *state['messages']])]}

    graph = StateGraph(MessagesState)
    graph.add_node('agent', agent)
    graph.add_node('tools', ToolNode(tools))
    graph.add_edge(START, 'agent')
    graph.add_conditional_edges('agent', tools_condition)
    graph.add_edge('tools', 'agent')
    return graph.compile()
