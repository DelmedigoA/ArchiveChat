"""Terminal chat over a compiled collection."""

import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from openai import APIError, NotFoundError

from ..cli_options import parse_chat_options
from .runtime import build_runtime
from .results import message_text


def main():
    load_dotenv()
    args = parse_chat_options(__doc__)
    graph = build_runtime(args)
    run_conversation(graph, args)


def run_conversation(graph, args):
    """Keep terminal history and handle one-shot or interactive questions."""
    messages = []
    while True:
        try:
            question = args.question if args.question else input('You: ').strip()
        except EOFError, KeyboardInterrupt:
            break
        if not question or question.casefold() in {'exit', 'quit'}:
            break
        try:
            result = graph.invoke(
                {'messages': [*messages, HumanMessage(content=question)]}, {'recursion_limit': 25}
            )
        except NotFoundError:
            print(
                f'Model {args.model!r} is unavailable to this API key. Choose another model with --model.',
                file=sys.stderr,
            )
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
        print('\nArchiveLens:', message_text(messages[-1].content), '\n')
        if args.question:
            break


if __name__ == '__main__':
    main()
