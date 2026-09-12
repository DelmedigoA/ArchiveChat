"""Tools for ArchiveLens project metadata retrieval."""

from langchain_core.tools import BaseTool, tool

from ..project_metadata import ProjectMetadataCollection


def make_project_metadata_tools(collection: ProjectMetadataCollection) -> list[BaseTool]:
    """Create tools for project and website context records."""

    @tool
    def list_project_metadata_records() -> list[dict]:
        """List project metadata records for ArchiveLens/Bearing Witness, including About, author, document, website navigation, sitemap crawl, and version context. These are not event evidence."""
        return collection.list_records()

    @tool
    def read_project_metadata_record(record_id: str) -> dict:
        """Read a project metadata record. Use first for project, website, author, Lee Mordechai, About, document, version, navigation, sitemap, and crawl questions; not event evidence."""
        return collection.read(record_id)

    return [list_project_metadata_records, read_project_metadata_record]
