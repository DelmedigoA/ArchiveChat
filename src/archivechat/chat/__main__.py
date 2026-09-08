"""Terminal chat over a compiled collection."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.errors import GraphRecursionError
from openai import APIError, NotFoundError

from .collection import Collection
from .documents import DOCUMENT_TEXT_PATH, DocumentCollection
from .faqs import FAQ_PATH, FaqCollection
from .graph import build_graph
from .results import message_text
from .web_tools import make_web_tools


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
    parser.add_argument('--question', help='Ask one question and exit')
    args = parser.parse_args()
    if not args.model:
        parser.error('Set ARCHIVECHAT_MODEL or pass --model with an OpenAI model supporting tools')
    if args.model.strip().upper() == 'YOUR_MODEL':
        parser.error('YOUR_MODEL is a placeholder. Omit --model to use gpt-5.')
    if not args.reasoning_effort:
        parser.error('Set ARCHIVECHAT_REASONING_EFFORT or pass --reasoning-effort')
    if not args.verbosity:
        parser.error('Set ARCHIVECHAT_VERBOSITY or pass --verbosity')
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
    document_collection = DocumentCollection(args.document_text) if args.document_text.exists() else None
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
    )
    messages = []
    while True:
        try:
            question = args.question if args.question else input('You: ').strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question or question.casefold() in {'exit', 'quit'}:
            break
        try:
            result = graph.invoke({'messages': [*messages, HumanMessage(content=question)]}, {'recursion_limit': 25})
        except NotFoundError:
            print(f'Model {args.model!r} is unavailable to this API key. Choose another model with --model.', file=sys.stderr)
            raise SystemExit(1) from None
        except APIError as exc:
            print(f'OpenAI request failed: {exc}', file=sys.stderr)
            raise SystemExit(1) from None
        except GraphRecursionError:
            print('Stopped: tool-round limit reached. Try a narrower question.')
            if args.question:
                raise SystemExit(1)
            continue
        messages = result['messages']
        print('\nArchiveChat:', message_text(messages[-1].content), '\n')
        if args.question:
            break


if __name__ == '__main__':
    main()
