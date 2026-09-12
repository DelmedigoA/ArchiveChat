"""Run the local ArchiveLens web UI."""

import uvicorn
from dotenv import load_dotenv

from archivelens.chat.runtime import build_runtime
from archivelens.cli_options import parse_chat_options

from .app import create_app


def main():
    load_dotenv()
    args = parse_chat_options(__doc__, web=True)
    graph = build_runtime(args)
    uvicorn.run(
        create_app(
            graph, document_pdf_url=args.document_pdf_url, document_pdf_path=args.document_pdf_path
        ),
        host=args.host,
        port=args.port,
    )


if __name__ == '__main__':
    main()
