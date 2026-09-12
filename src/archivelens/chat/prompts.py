"""Prompt loading for the chat graph."""

from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parents[3] / 'data' / 'prompts'


def load_chat_prompt(prompt_dir: Path = PROMPT_DIR, include_document: bool = False) -> str:
    system = (prompt_dir / 'system.md').read_text().strip()
    instructions = (prompt_dir / 'instructions.md').read_text().strip()
    if include_document:
        instructions = f'{instructions}\n\n{(prompt_dir / "document-instructions.md").read_text().strip()}'
    return f'{system}\n\n{instructions}'
