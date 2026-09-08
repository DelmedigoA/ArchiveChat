"""Prompt loading for the chat graph."""

from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parents[3] / 'data' / 'prompts'


def load_chat_prompt(prompt_dir: Path = PROMPT_DIR) -> str:
    system = (prompt_dir / 'system.md').read_text().strip()
    instructions = (prompt_dir / 'instructions.md').read_text().strip()
    return f'{system}\n\n{instructions}'
