"""Construct the shared chat graph from resolved command-line options."""

from argparse import Namespace

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .collection import Collection
from .embeddings import CachedEmbeddings
from .documents import DocumentCollection
from .faqs import FaqCollection
from .graph import build_graph
from .project_metadata import ProjectMetadataCollection
from .web_tools import make_web_tools


def build_runtime(args: Namespace):
    """Load collections, configure providers, and connect the graph's tools."""
    embeddings = None
    if args.semantic_search:
        backend = OpenAIEmbeddings(model=args.embedding_model, timeout=60, max_retries=1)
        embeddings = CachedEmbeddings(backend, args.embedding_cache, args.embedding_model)
    collection = Collection(args.collection, embeddings=embeddings)
    faq_collection = FaqCollection(args.faq_file)
    document_collection = None
    if args.include_document and args.document_text.exists():
        document_collection = DocumentCollection(args.document_text, embeddings=embeddings)
    project_metadata_collection = None
    if args.project_metadata_file.exists():
        project_metadata_collection = ProjectMetadataCollection(args.project_metadata_file)
    model_kwargs = {
        'model': args.model,
        'timeout': 60,
        'max_retries': 1,
        'verbosity': args.verbosity,
        'use_responses_api': args.reasoning_effort != 'none',
    }
    if args.reasoning_effort != 'none':
        model_kwargs['reasoning_effort'] = args.reasoning_effort
    return build_graph(
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
