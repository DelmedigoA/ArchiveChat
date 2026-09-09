"""Run the local ArchiveLens web UI."""

import argparse
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from archivechat.chat.collection import CachedEmbeddings, Collection
from archivechat.chat.documents import DOCUMENT_TEXT_PATH, DocumentCollection
from archivechat.chat.faqs import FAQ_PATH, FaqCollection
from archivechat.chat.graph import build_graph
from archivechat.chat.project_metadata import PROJECT_METADATA_PATH, ProjectMetadataCollection
from archivechat.chat.web_tools import make_web_tools
from archivechat.config import apply_config, load_config

from .app import DOCUMENT_PDF_PATH, DOCUMENT_PDF_ROUTE, create_app


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--collection', type=Path)
    parser.add_argument('--model')
    parser.add_argument('--reasoning-effort')
    parser.add_argument('--verbosity')
    parser.add_argument('--search-limit', type=int)
    parser.add_argument('--semantic-search', action='store_true', default=None)
    parser.add_argument('--embedding-model')
    parser.add_argument('--embedding-cache', type=Path)
    parser.add_argument('--web-tools', action='store_true', default=None)
    parser.add_argument('--faq-file', type=Path)
    parser.add_argument('--faq-search-limit', type=int)
    parser.add_argument('--document-text', type=Path)
    parser.add_argument('--document-pdf-url')
    parser.add_argument('--document-pdf-path', type=Path)
    parser.add_argument('--include-document', action='store_true', default=None)
    parser.add_argument('--document-search-limit', type=int)
    parser.add_argument('--project-metadata-file', type=Path)
    parser.add_argument('--host')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    config = load_config(args.config)
    apply_config(args, config)
    args.collection = Path(args.collection or 'data/archiveai/compiled/items')
    args.model = args.model or os.getenv('ARCHIVECHAT_MODEL') or 'gpt-5'
    args.reasoning_effort = args.reasoning_effort or os.getenv('ARCHIVECHAT_REASONING_EFFORT') or 'low'
    args.verbosity = args.verbosity or os.getenv('ARCHIVECHAT_VERBOSITY') or 'low'
    args.search_limit = args.search_limit if args.search_limit is not None else int(os.getenv('ARCHIVECHAT_SEARCH_LIMIT') or '10')
    args.semantic_search = bool(args.semantic_search or os.getenv('ARCHIVECHAT_SEMANTIC_SEARCH') == 'true')
    args.embedding_model = args.embedding_model or os.getenv('ARCHIVECHAT_EMBEDDING_MODEL') or 'text-embedding-3-small'
    args.embedding_cache = Path(args.embedding_cache or os.getenv('ARCHIVECHAT_EMBEDDING_CACHE') or 'data/index/embeddings.json')
    args.web_tools = bool(args.web_tools or os.getenv('ARCHIVECHAT_WEB_TOOLS') == 'true')
    args.faq_file = Path(args.faq_file or os.getenv('ARCHIVECHAT_FAQ_FILE') or FAQ_PATH)
    args.faq_search_limit = args.faq_search_limit if args.faq_search_limit is not None else int(os.getenv('ARCHIVECHAT_FAQ_SEARCH_LIMIT') or '5')
    args.document_text = Path(args.document_text or os.getenv('ARCHIVECHAT_DOCUMENT_TEXT') or DOCUMENT_TEXT_PATH)
    args.document_pdf_url = args.document_pdf_url or os.getenv('ARCHIVECHAT_DOCUMENT_PDF_URL') or DOCUMENT_PDF_ROUTE
    args.document_pdf_path = Path(args.document_pdf_path or os.getenv('ARCHIVECHAT_DOCUMENT_PDF_PATH') or DOCUMENT_PDF_PATH)
    args.include_document = bool(args.include_document or os.getenv('ARCHIVECHAT_INCLUDE_DOCUMENT') == 'true')
    args.document_search_limit = args.document_search_limit if args.document_search_limit is not None else int(os.getenv('ARCHIVECHAT_DOCUMENT_SEARCH_LIMIT') or '5')
    args.project_metadata_file = Path(args.project_metadata_file or os.getenv('ARCHIVECHAT_PROJECT_METADATA_FILE') or PROJECT_METADATA_PATH)
    args.host = args.host or '127.0.0.1'
    args.port = args.port or 8765

    if args.search_limit < 1:
        parser.error('--search-limit must be at least 1')
    if args.faq_search_limit < 1:
        parser.error('--faq-search-limit must be at least 1')
    if args.document_search_limit < 1:
        parser.error('--document-search-limit must be at least 1')
    if not os.getenv('OPENAI_API_KEY'):
        parser.error('Set OPENAI_API_KEY in your environment or .env')

    embeddings = None
    if args.semantic_search:
        embeddings = CachedEmbeddings(OpenAIEmbeddings(model=args.embedding_model, timeout=60, max_retries=1), args.embedding_cache, args.embedding_model)
    collection = Collection(args.collection, embeddings=embeddings)
    faq_collection = FaqCollection(args.faq_file)
    document_collection = DocumentCollection(args.document_text, embeddings=embeddings) if args.include_document and args.document_text.exists() else None
    project_metadata_collection = ProjectMetadataCollection(args.project_metadata_file) if args.project_metadata_file.exists() else None
    model_kwargs = {
        'model': args.model,
        'timeout': 60,
        'max_retries': 1,
        'verbosity': args.verbosity,
        'use_responses_api': args.reasoning_effort != 'none',
    }
    if args.reasoning_effort != 'none':
        model_kwargs['reasoning_effort'] = args.reasoning_effort
    graph = build_graph(
        collection,
        ChatOpenAI(**model_kwargs),
        search_limit=args.search_limit,
        extra_tools=make_web_tools() if args.web_tools else None,
        faq_collection=faq_collection,
        faq_search_limit=args.faq_search_limit,
        document_collection=document_collection,
        include_document=args.include_document,
        document_search_limit=args.document_search_limit,
        project_metadata_collection=project_metadata_collection,
    )
    uvicorn.run(
        create_app(graph, document_pdf_url=args.document_pdf_url, document_pdf_path=args.document_pdf_path),
        host=args.host,
        port=args.port,
    )


if __name__ == '__main__':
    main()
