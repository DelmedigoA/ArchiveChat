"""Tools for FAQ metadata retrieval."""

from langchain_core.tools import BaseTool, tool

from ..faqs import FaqCollection


def make_faq_tools(collection: FaqCollection, search_limit: int = 5) -> list[BaseTool]:
    """Create tools for FAQ metadata retrieval."""
    if search_limit < 1:
        raise ValueError('faq_search_limit must be at least 1')

    @tool
    def search_faqs(query: str, limit: int = search_limit) -> list[dict]:
        """Find FAQ metadata questions relevant to project context, methodology, scope, or usage."""
        return collection.search(query, limit)

    @tool
    def read_faq(faq_id: str) -> dict:
        """Read the full FAQ metadata answer for a question returned by search_faqs."""
        return collection.read(faq_id)

    return [search_faqs, read_faq]
