"""Run the local ArchiveLens web UI."""

import argparse
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from archivechat.chat.collection import Collection
from archivechat.chat.documents import DOCUMENT_TEXT_PATH, DocumentCollection
from archivechat.chat.faqs import FAQ_PATH, FaqCollection
from archivechat.chat.graph import build_graph
from archivechat.chat.project_metadata import PROJECT_METADATA_PATH, ProjectMetadataCollection
from archivechat.chat.web_tools import make_web_tools

from .app import create_app


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=Path, default=Path('data/archiveai/compiled/items'))
    parser.add_argument('--model', default=os.getenv('ARCHIVECHAT_MODEL') or 'gpt-5')
    parser.add_argument('--reasoning-effort', default=os.getenv('ARCHIVECHAT_REASONING_EFFORT') or 'low')
    parser.add_argument('--verbosity', default=os.getenv('ARCHIVECHAT_VERBOSITY') or 'low')
    parser.add_argument('--search-limit', type=int, default=int(os.getenv('ARCHIVECHAT_SEARCH_LIMIT') or '10'))
    parser.add_argument('--semantic-search', action='store_true', default=os.getenv('ARCHIVECHAT_SEMANTIC_SEARCH') == 'true')
    parser.add_argument('--embedding-model', default=os.getenv('ARCHIVECHAT_EMBEDDING_MODEL') or 'text-embedding-3-small')
    parser.add_argument('--web-tools', action='store_true', default=os.getenv('ARCHIVECHAT_WEB_TOOLS') == 'true')
    parser.add_argument('--faq-file', type=Path, default=Path(os.getenv('ARCHIVECHAT_FAQ_FILE') or FAQ_PATH))
    parser.add_argument('--faq-search-limit', type=int, default=int(os.getenv('ARCHIVECHAT_FAQ_SEARCH_LIMIT') or '5'))
    parser.add_argument('--document-text', type=Path, default=Path(os.getenv('ARCHIVECHAT_DOCUMENT_TEXT') or DOCUMENT_TEXT_PATH))
    parser.add_argument('--document-search-limit', type=int, default=int(os.getenv('ARCHIVECHAT_DOCUMENT_SEARCH_LIMIT') or '5'))
    parser.add_argument('--project-metadata-file', type=Path, default=Path(os.getenv('ARCHIVECHAT_PROJECT_METADATA_FILE') or PROJECT_METADATA_PATH))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()

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
        embeddings = OpenAIEmbeddings(model=args.embedding_model, timeout=60, max_retries=1)
    collection = Collection(args.collection, embeddings=embeddings)
    faq_collection = FaqCollection(args.faq_file)
    document_collection = DocumentCollection(args.document_text, embeddings=embeddings) if args.document_text.exists() else None
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
        document_search_limit=args.document_search_limit,
        project_metadata_collection=project_metadata_collection,
    )
    uvicorn.run(create_app(graph), host=args.host, port=args.port)


if __name__ == '__main__':
    main()
