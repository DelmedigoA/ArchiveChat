"""CLI/YAML/environment options shared by the terminal and web entry points."""

import argparse
import os
from pathlib import Path

from .chat.documents import DOCUMENT_TEXT_PATH
from .chat.faqs import FAQ_PATH
from .chat.project_metadata import PROJECT_METADATA_PATH
from .config import apply_config, load_config


def parse_chat_options(description: str, *, web: bool = False) -> argparse.Namespace:
    """Parse options without loading collections, constructing models, or running chat."""
    parser = argparse.ArgumentParser(description=description)
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
    if web:
        parser.add_argument('--document-pdf-url')
        parser.add_argument('--document-pdf-path', type=Path)
    parser.add_argument('--include-document', action='store_true', default=None)
    parser.add_argument('--document-search-limit', type=int)
    parser.add_argument('--project-metadata-file', type=Path)
    if web:
        parser.add_argument('--host')
        parser.add_argument('--port', type=int)
    else:
        parser.add_argument('--question', help='Ask one question and exit')
    args = parser.parse_args()
    apply_config(args, load_config(args.config))
    resolve_chat_defaults(args)
    if web:
        from .web.app import DOCUMENT_PDF_PATH, DOCUMENT_PDF_ROUTE

        args.document_pdf_url = (
            args.document_pdf_url or os.getenv('ARCHIVECHAT_DOCUMENT_PDF_URL') or DOCUMENT_PDF_ROUTE
        )
        args.document_pdf_path = Path(
            args.document_pdf_path
            or os.getenv('ARCHIVECHAT_DOCUMENT_PDF_PATH')
            or DOCUMENT_PDF_PATH
        )
        args.host = args.host or '127.0.0.1'
        args.port = args.port or 8765
    else:
        validate_terminal_options(parser, args)
    validate_chat_options(parser, args)
    return args


def resolve_chat_defaults(args: argparse.Namespace) -> None:
    """Apply existing environment fallbacks after CLI and YAML values.

    Boolean switches intentionally also honor an environment value of "true",
    even when YAML supplies false. Keep this legacy precedence explicit.
    """
    args.collection = Path(args.collection or 'data/archiveai/compiled/items')
    args.model = args.model or os.getenv('ARCHIVECHAT_MODEL') or 'gpt-5'
    args.reasoning_effort = (
        args.reasoning_effort or os.getenv('ARCHIVECHAT_REASONING_EFFORT') or 'low'
    )
    args.verbosity = args.verbosity or os.getenv('ARCHIVECHAT_VERBOSITY') or 'low'
    args.search_limit = (
        args.search_limit
        if args.search_limit is not None
        else int(os.getenv('ARCHIVECHAT_SEARCH_LIMIT') or '10')
    )
    args.semantic_search = bool(
        args.semantic_search or os.getenv('ARCHIVECHAT_SEMANTIC_SEARCH') == 'true'
    )
    args.embedding_model = (
        args.embedding_model or os.getenv('ARCHIVECHAT_EMBEDDING_MODEL') or 'text-embedding-3-small'
    )
    args.embedding_cache = Path(
        args.embedding_cache
        or os.getenv('ARCHIVECHAT_EMBEDDING_CACHE')
        or 'data/index/embeddings.json'
    )
    args.web_tools = bool(args.web_tools or os.getenv('ARCHIVECHAT_WEB_TOOLS') == 'true')
    args.faq_file = Path(args.faq_file or os.getenv('ARCHIVECHAT_FAQ_FILE') or FAQ_PATH)
    args.faq_search_limit = (
        args.faq_search_limit
        if args.faq_search_limit is not None
        else int(os.getenv('ARCHIVECHAT_FAQ_SEARCH_LIMIT') or '5')
    )
    args.document_text = Path(
        args.document_text or os.getenv('ARCHIVECHAT_DOCUMENT_TEXT') or DOCUMENT_TEXT_PATH
    )
    args.include_document = bool(
        args.include_document or os.getenv('ARCHIVECHAT_INCLUDE_DOCUMENT') == 'true'
    )
    args.document_search_limit = (
        args.document_search_limit
        if args.document_search_limit is not None
        else int(os.getenv('ARCHIVECHAT_DOCUMENT_SEARCH_LIMIT') or '5')
    )
    args.project_metadata_file = Path(
        args.project_metadata_file
        or os.getenv('ARCHIVECHAT_PROJECT_METADATA_FILE')
        or PROJECT_METADATA_PATH
    )


def validate_terminal_options(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Retain the terminal's additional model checks."""
    if not args.model:
        parser.error('Set ARCHIVECHAT_MODEL or pass --model with an OpenAI model supporting tools')
    if args.model.strip().upper() == 'YOUR_MODEL':
        parser.error('YOUR_MODEL is a placeholder. Omit --model to use gpt-5.')
    if not args.reasoning_effort:
        parser.error('Set ARCHIVECHAT_REASONING_EFFORT or pass --reasoning-effort')
    if not args.verbosity:
        parser.error('Set ARCHIVECHAT_VERBOSITY or pass --verbosity')


def validate_chat_options(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.search_limit < 1:
        parser.error('--search-limit must be at least 1')
    if args.faq_search_limit < 1:
        parser.error('--faq-search-limit must be at least 1')
    if args.document_search_limit < 1:
        parser.error('--document-search-limit must be at least 1')
    if not os.getenv('OPENAI_API_KEY'):
        parser.error('Set OPENAI_API_KEY in your environment or .env')
