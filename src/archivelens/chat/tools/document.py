"""Tools for Bearing Witness document retrieval."""

from langchain_core.tools import BaseTool, tool

from ..documents import DocumentCollection


def make_document_tools(collection: DocumentCollection, search_limit: int = 5) -> list[BaseTool]:
    """Create tools for page-level Bearing Witness document retrieval."""
    if search_limit < 1:
        raise ValueError('document_search_limit must be at least 1')

    @tool
    def search_bearing_witness_document(query: str, limit: int = search_limit) -> list[dict]:
        """Find matching pages in the Bearing Witness Gaza document. Returns page matches, not full text."""
        return collection.search(query, limit)

    @tool
    def read_bearing_witness_pages(start_page: int, end_page: int | None = None) -> dict:
        """Read full text from selected Bearing Witness document pages."""
        return collection.read_pages(start_page, end_page)

    return [search_bearing_witness_document, read_bearing_witness_pages]
