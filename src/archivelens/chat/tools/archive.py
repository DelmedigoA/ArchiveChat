"""Tools for archive item retrieval."""

from langchain_core.tools import BaseTool, tool

from ..collection import Collection


def make_archive_tools(collection: Collection, search_limit: int = 10) -> list[BaseTool]:
    """Create tools for searching and reading archive items."""
    if search_limit < 1:
        raise ValueError('search_limit must be at least 1')

    @tool
    def search_items(query: str, limit: int = search_limit) -> list[dict]:
        """Find candidate items by keywords in catalog metadata and article text."""
        return collection.search(query, limit)

    @tool
    def read_item(item_id: str) -> dict:
        """Read an entire item, including its catalog and full source content."""
        return collection.read(item_id)

    return [search_items, read_item]
